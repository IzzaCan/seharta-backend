import string
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func

from app.models.user import User
from app.models.family import Family, PairingCode
from app.schemas.family import CreateFamilyRequest, JoinFamilyRequest, UpdateFamilyNameRequest


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
