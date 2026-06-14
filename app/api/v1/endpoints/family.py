import string
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.api import dependencies
from app.db.session import get_db
from app.models.user import User
from app.models.family import Family, PairingCode
from app.schemas.family import CreateFamilyRequest, JoinFamilyRequest, FamilyCreateResponse, FamilyJoinResponse, FamilyResponse, UpdateFamilyNameRequest, RegenerateCodeResponse, LeaveFamilyResponse

router = APIRouter()

def generate_unique_pin(db: Session) -> str:
    """Generate 6-digit PIN acak (Secure) dan pastikan unik di database."""
    while True:
        code = ''.join(secrets.choice(string.digits) for _ in range(6))
        existing_code = db.execute(
            select(PairingCode).where(PairingCode.code == code)
        ).scalar_one_or_none()
        if not existing_code:
            return code

@router.post("/create", response_model=FamilyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_family(
    request: CreateFamilyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user)
) -> Any:
    """
    Create a new family and generate a 6-digit pairing code.
    """
    if current_user.family_id:
        raise HTTPException(status_code=400, detail="User sudah tergabung dalam dompet bersama")

    try:
        new_family = Family(family_name=request.family_name)
        db.add(new_family)
        db.flush()

        pin_code = generate_unique_pin(db)
        expiration_time = datetime.now(timezone.utc) + timedelta(hours=24)
        
        new_pairing = PairingCode(
            family_id=new_family.id,
            code=pin_code,
            expires_at=expiration_time
        )
        db.add(new_pairing)
        
        current_user.family_id = new_family.id
        db.commit()
        
        return FamilyCreateResponse(message="Keluarga berhasil dibuat", code=pin_code)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Terjadi kesalahan internal server.")

@router.post("/join", response_model=FamilyJoinResponse, status_code=status.HTTP_200_OK)
def join_family(
    request: JoinFamilyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user)
) -> Any:
    """
    Join an existing family using a 6-digit pairing code.
    """
    if current_user.family_id:
        raise HTTPException(status_code=400, detail="User sudah tergabung dalam dompet bersama")

    try:
        pairing = db.execute(
            select(PairingCode)
            .where(PairingCode.code == request.code)
            .where(PairingCode.is_used == False)
            .where(PairingCode.expires_at > datetime.now(timezone.utc))
            .with_for_update() 
        ).scalar_one_or_none()
        
        if not pairing:
            db.rollback()
            raise HTTPException(status_code=400, detail="PIN tidak valid atau sudah kedaluwarsa")
            
        current_user.family_id = pairing.family_id
        pairing.is_used = True
        pairing.used_by = current_user.id
        pairing.used_at = datetime.now(timezone.utc)
        
        db.commit()
        
        return FamilyJoinResponse(message="Berhasil bergabung dengan dompet bersama!", family_id=pairing.family_id)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Terjadi kesalahan internal server.")

@router.get("/pairing-status/{code}")
def get_pairing_status(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user)
) -> Any:
    """
    Check if the pairing code has been used.
    """
    pairing = db.execute(
        select(PairingCode)
        .where(PairingCode.code == code)
    ).scalar_one_or_none()
    
    if not pairing:
        raise HTTPException(status_code=404, detail="PIN tidak ditemukan")
        
    if pairing.family_id != current_user.family_id:
        raise HTTPException(status_code=403, detail="Tidak memiliki akses ke PIN ini")
        
    return {"is_used": pairing.is_used}

@router.get("/info", response_model=FamilyResponse)
def get_family_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user)
) -> Any:
    """
    Get the family information of the current user.
    """
    if not current_user.family_id:
        raise HTTPException(status_code=404, detail="User tidak tergabung dalam keluarga")
        
    family = db.execute(
        select(Family).where(Family.id == current_user.family_id)
    ).scalar_one_or_none()
    
    if not family:
        raise HTTPException(status_code=404, detail="Keluarga tidak ditemukan")
        
    return family

@router.put("/name", response_model=FamilyResponse)
def update_family_name(
    request: UpdateFamilyNameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user)
) -> Any:
    """
    Update the family name of the current user's family.
    """
    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="User tidak tergabung dalam keluarga")
        
    family = db.execute(
        select(Family).where(Family.id == current_user.family_id)
    ).scalar_one_or_none()
    
    if not family:
        raise HTTPException(status_code=404, detail="Keluarga tidak ditemukan")
    
    try:
        family.family_name = request.family_name
        db.commit()
        db.refresh(family)
        return family
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Terjadi kesalahan internal server.")

@router.post("/regenerate-code", response_model=RegenerateCodeResponse)
def regenerate_code(
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user)
) -> Any:
    """
    Regenerate a pairing code for the family.
    """
    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="User tidak tergabung dalam keluarga")

    try:
        pin_code = generate_unique_pin(db)
        expiration_time = datetime.now(timezone.utc) + timedelta(hours=24)
        
        new_pairing = PairingCode(
            family_id=current_user.family_id,
            code=pin_code,
            expires_at=expiration_time
        )
        db.add(new_pairing)
        db.commit()
        
        return RegenerateCodeResponse(
            message="Pairing code generated successfully",
            code=pin_code,
            expires_at=expiration_time
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Terjadi kesalahan internal server.")

@router.post("/leave", response_model=LeaveFamilyResponse)
def leave_family(
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user)
) -> Any:
    """
    Leave the current family.
    """
    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="User tidak tergabung dalam keluarga")

    try:
        family_id = current_user.family_id
        current_user.family_id = None
        db.flush()
        
        remaining_members = db.execute(
            select(func.count(User.id)).where(User.family_id == family_id)
        ).scalar()
        
        if remaining_members == 0:
            family_to_delete = db.execute(
                select(Family).where(Family.id == family_id)
            ).scalar_one_or_none()
            if family_to_delete:
                db.delete(family_to_delete)
        
        db.commit()
        
        return LeaveFamilyResponse(message="Successfully left the family")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Terjadi kesalahan internal server.")
