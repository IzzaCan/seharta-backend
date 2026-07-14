import string
import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from uuid import UUID
import logging
import os
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func

from app.models.user import User
from app.models.family import Family, PairingCode
from app.models.asset import Asset, OwnershipType
from app.schemas.family import CreateFamilyRequest, JoinFamilyRequest, UpdateFamilyNameRequest
from app.utils.pdf_generator import generate_liquidation_pdf

logger = logging.getLogger(__name__)


class FamilyService:
    """Business logic for family operations."""

    def __init__(self, db: Session):
        self.db = db

    def _generate_unique_pin(self) -> str:
        """
        Generate 6-digit PIN and ensure it is globally unique across the entire table
        to satisfy the database unique constraint.
        """
        while True:
            code = ''.join(secrets.choice(string.digits) for _ in range(6))
            existing_code = self.db.execute(
                select(PairingCode)
                .where(PairingCode.code == code)
            ).scalar_one_or_none()
            if not existing_code:
                return code

    def create_family(self, current_user: User, request: CreateFamilyRequest) -> str:
        if current_user.family_id:
            raise HTTPException(status_code=400, detail="User sudah tergabung dalam dompet bersama")

        try:
            new_family = Family(family_name=request.family_name)
            self.db.add(new_family)
            self.db.flush()

            pin_code = self._generate_unique_pin()

            new_pairing = PairingCode(
                family_id=new_family.id,
                code=pin_code
            )
            self.db.add(new_pairing)

            current_user.family_id = new_family.id

            # Lazy import WalletService to prevent circular dependencies
            from app.services.wallet_service import WalletService
            wallet_service = WalletService(self.db)
            wallet_service.create_bootstrap_wallet(new_family.id)

            self.db.commit()
            return pin_code

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            raise e

    def join_family(self, current_user: User, request: JoinFamilyRequest) -> UUID:
        if current_user.family_id:
            raise HTTPException(status_code=400, detail="User sudah tergabung dalam dompet bersama")

        try:
            pairing = self.db.execute(
                select(PairingCode)
                .where(PairingCode.code == request.code)
            ).scalar_one_or_none()

            if not pairing:
                raise HTTPException(status_code=400, detail="PIN tidak valid")

            current_user.family_id = pairing.family_id

            self.db.commit()
            return pairing.family_id

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            raise e

    def get_family_info(self, current_user: User) -> Family:
        if not current_user.family_id:
            raise HTTPException(status_code=400, detail="User tidak tergabung dalam dompet bersama")

        family = self.db.execute(
            select(Family).options(selectinload(Family.users)).where(Family.id == current_user.family_id)
        ).scalar_one_or_none()

        if not family:
            raise HTTPException(status_code=404, detail="Keluarga tidak ditemukan")

        return family

    def update_family_name(self, current_user: User, request: UpdateFamilyNameRequest) -> Family:
        if not current_user.family_id:
            raise HTTPException(status_code=400, detail="User tidak tergabung dalam dompet bersama")

        try:
            family = self.db.execute(
                select(Family).options(selectinload(Family.users)).where(Family.id == current_user.family_id)
            ).scalar_one_or_none()

            if not family:
                raise HTTPException(status_code=404, detail="Keluarga tidak ditemukan")

            family.family_name = request.family_name
            self.db.commit()
            self.db.refresh(family)
            return family

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            raise e

    def leave_family(self, current_user: User) -> None:
        if not current_user.family_id:
            raise HTTPException(status_code=400, detail="User tidak tergabung dalam dompet bersama")

        try:
            family_id = current_user.family_id
            current_user.family_id = None
            self.db.flush()

            remaining_members = self.db.execute(
                select(func.count(User.id)).where(User.family_id == family_id)
            ).scalar()

            if remaining_members == 0:
                family_to_delete = self.db.execute(
                    select(Family).where(Family.id == family_id)
                ).scalar_one_or_none()
                if family_to_delete:
                    self.db.delete(family_to_delete)

            self.db.commit()

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            raise e

    def unlink_family(self, current_user: User) -> tuple[dict, list[str]]:
        if not current_user.family_id:
            raise HTTPException(status_code=400, detail="User tidak tergabung dalam dompet bersama")

        family_id = current_user.family_id
        
        try:
            # 1. Row Locking: Lock Family and User records to prevent race conditions
            family = self.db.execute(
                select(Family).where(Family.id == family_id).with_for_update()
            ).scalar_one_or_none()
            
            if not family:
                raise HTTPException(status_code=400, detail="Keluarga tidak ditemukan atau sudah dihapus")
            
            members = self.db.execute(
                select(User).where(User.family_id == family_id).with_for_update()
            ).scalars().all()
            
            if len(members) < 2:
                raise HTTPException(status_code=400, detail="Anggota keluarga kurang dari 2")
                
            member_names = [m.full_name for m in members]
            member_emails = [m.email for m in members]
            
            # 2. Query Assets
            assets = self.db.execute(
                select(Asset).where(Asset.family_id == family_id)
            ).scalars().all()
            
            personal_assets = []
            joint_assets = []
            total_joint = 0.0
            
            # Prepare DTOs for PDF Generation to avoid DetachedInstanceError
            for asset in assets:
                asset_dict = {
                    "asset_name": asset.asset_name,
                    "valuation": float(asset.purchase_price),
                    "owner_name": asset.owner_name
                }
                
                if asset.ownership_type == OwnershipType.PERSONAL:
                    personal_assets.append(asset_dict)
                else:
                    joint_assets.append(asset_dict)
                    total_joint += float(asset.purchase_price)
            
            claim_per_person = total_joint / 2 if total_joint > 0 else 0.0
            
            # 3. Generate PDF
            tz = ZoneInfo("Asia/Jakarta")
            settled_at = datetime.now(tz)
            
            doc_number = f"LIQ-{family_id}-{settled_at.strftime('%Y%m%d%H%M%S')}"
            
            pdf_url = generate_liquidation_pdf(
                family_id=str(family_id),
                family_name=family.family_name,
                member_names=member_names,
                personal_assets=personal_assets,
                joint_assets=joint_assets,
                total_joint=total_joint,
                claim_per_person=claim_per_person,
                timestamp=settled_at.isoformat(),
                doc_number=doc_number
            )
            
            # 4. Eksekusi Pemusnahan (Database) & Cleanup Fallback
            for member in members:
                member.family_id = None
                
            self.db.delete(family)
            self.db.commit()
            
            logger.info("Family %s successfully unlinked by user %s", family_id, current_user.id)
            
            return {
                "pdf_url": pdf_url,
                "total_joint_asset_value": total_joint,
                "claim_per_person": claim_per_person,
                "member_count": len(members),
                "settled_at": settled_at
            }, member_emails
            
        except Exception:
            self.db.rollback()
            # COMPENSATING ACTION: Hapus orphan file PDF
            if 'pdf_url' in locals():
                BASE_DIR = Path(__file__).resolve().parent.parent.parent
                # PDF URL format: /static/reports/...
                pdf_path = BASE_DIR / "app" / pdf_url.lstrip("/")
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
                    
            logger.exception("Gagal memutus tautan keluarga.")
            raise
