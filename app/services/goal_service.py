from decimal import Decimal
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app.models.goal import Goal
from app.models.goal_contribution import GoalContribution
from app.models.transaction import Transaction, TransactionType
from app.models.wallet import Wallet
from app.models.user import User
from app.schemas.goal import GoalCreate, GoalUpdate, GoalContributionCreate

class GoalService:
    def __init__(self, db: Session):
        self.db = db

    def _lock_goal(self, goal_id: UUID, family_id: UUID) -> Goal:
        goal = self.db.execute(
            select(Goal)
            .where(Goal.id == goal_id, Goal.family_id == family_id)
            .with_for_update()
        ).scalar_one_or_none()
        if not goal:
            raise HTTPException(status_code=404, detail="Goal tidak ditemukan")
        return goal

    def _lock_wallet(self, wallet_id: UUID, family_id: UUID) -> Wallet:
        wallet = self.db.execute(
            select(Wallet)
            .where(Wallet.id == wallet_id, Wallet.family_id == family_id)
            .with_for_update()
        ).scalar_one_or_none()
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet tidak ditemukan")
        if not wallet.is_active:
            raise HTTPException(status_code=400, detail="Wallet tidak aktif")
        return wallet

    def create_goal(self, user: User, data: GoalCreate) -> Goal:
        goal = Goal(
            family_id=user.family_id,
            created_by=user.id,
            name=data.name,
            target_amount=Decimal(str(data.target_amount)),
            deadline=data.deadline,
            note=data.note
        )
        self.db.add(goal)
        try:
            self.db.flush()
            
            from app.services.notification_service import NotificationService
            from app.schemas.notification import NotificationCreate
            from app.models.notification import NotificationType
            NotificationService.create_notification(
                self.db,
                NotificationCreate(
                    title="Goal Dibuat",
                    message=f"Goal '{goal.name}' dengan target {float(goal.target_amount):,.2f} telah dibuat.",
                    type=NotificationType.ACTIVITY,
                    family_id=user.family_id,
                    actor_user_id=user.id,
                    metadata_payload={
                        "goal_id": str(goal.id),
                        "name": goal.name,
                        "target_amount": float(goal.target_amount)
                    }
                )
            )
            
            self.db.commit()
            self.db.refresh(goal)
            return goal
        except Exception as e:
            self.db.rollback()
            raise e

    def update_goal(self, user: User, goal_id: UUID, data: GoalUpdate) -> Goal:
        goal = self._lock_goal(goal_id, user.family_id)
        
        if data.name is not None:
            goal.name = data.name
        if data.deadline is not None:
            goal.deadline = data.deadline
        if data.note is not None:
            goal.note = data.note
            
        if data.target_amount is not None:
            new_target = Decimal(str(data.target_amount))
            if new_target < Decimal(str(goal.current_amount)):
                self.db.rollback()
                raise HTTPException(status_code=400, detail="Target amount tidak boleh lebih kecil dari current amount")
            goal.target_amount = new_target

        try:
            self.db.flush()
            
            changes = []
            if data.name is not None: changes.append(f"nama menjadi '{goal.name}'")
            if data.target_amount is not None: changes.append(f"target menjadi {float(goal.target_amount):,.2f}")
            if data.deadline is not None: changes.append(f"tenggat waktu menjadi {goal.deadline.strftime('%Y-%m-%d') if goal.deadline else 'none'}")
            
            if changes:
                from app.services.notification_service import NotificationService
                from app.schemas.notification import NotificationCreate
                from app.models.notification import NotificationType
                NotificationService.create_notification(
                    self.db,
                    NotificationCreate(
                        title="Goal Diperbarui",
                        message=f"Goal '{goal.name}' diperbarui: " + ", ".join(changes) + ".",
                        type=NotificationType.ACTIVITY,
                        family_id=user.family_id,
                        actor_user_id=user.id,
                        metadata_payload={
                            "goal_id": str(goal.id),
                            "name": goal.name,
                            "target_amount": float(goal.target_amount)
                        }
                    )
                )

            self.db.commit()
            self.db.refresh(goal)
            return goal
        except Exception as e:
            self.db.rollback()
            raise e

    def add_contribution(self, user: User, goal_id: UUID, data: GoalContributionCreate) -> GoalContribution:
        goal = self._lock_goal(goal_id, user.family_id)
        
        wallet = None
        txn = None
        amount = Decimal(str(data.amount))
        
        if data.wallet_id:
            wallet = self._lock_wallet(data.wallet_id, user.family_id)
            
            # Create transaction
            txn = Transaction(
                family_id=user.family_id,
                wallet_id=wallet.id,
                user_id=user.id,
                amount=amount,
                transaction_type=TransactionType.TRANSFER,
                description=f"Transfer untuk Goal: {goal.name} - {data.note or ''}".strip(),
                transaction_date=data.contribution_date or datetime.now(timezone.utc),
                category_id=None # internal transfer
            )
            self.db.add(txn)
            
            if data.transaction_type == "DEPOSIT":
                new_balance = Decimal(str(wallet.balance)) - amount
                if new_balance < 0:
                    self.db.rollback()
                    raise HTTPException(status_code=400, detail="Saldo wallet tidak mencukupi")
                wallet.balance = new_balance
            else: # WITHDRAWAL
                wallet.balance = Decimal(str(wallet.balance)) + amount

        # Update Goal balance
        if data.transaction_type == "DEPOSIT":
            goal.current_amount = Decimal(str(goal.current_amount)) + amount
        else: # WITHDRAWAL
            new_goal_amount = Decimal(str(goal.current_amount)) - amount
            if new_goal_amount < 0:
                self.db.rollback()
                raise HTTPException(status_code=400, detail="Current amount goal tidak mencukupi untuk withdrawal")
            goal.current_amount = new_goal_amount

        contribution = GoalContribution(
            goal_id=goal.id,
            contributor_id=user.id,
            wallet_id=data.wallet_id,
            transaction_id=None, # Will set after flush
            amount=amount,
            transaction_type=data.transaction_type,
            note=data.note,
            contribution_date=data.contribution_date or datetime.now(timezone.utc)
        )
        self.db.add(contribution)
        
        try:
            self.db.flush()
            if txn:
                contribution.transaction_id = txn.id
                
            from app.services.notification_service import NotificationService
            from app.schemas.notification import NotificationCreate
            from app.models.notification import NotificationType
            
            action_str = "Deposit" if data.transaction_type == "DEPOSIT" else "Withdrawal"
            NotificationService.create_notification(
                self.db,
                NotificationCreate(
                    title=f"Kontribusi Goal ({action_str})",
                    message=f"{action_str} sebesar {float(amount):,.2f} untuk Goal '{goal.name}' berhasil dilakukan.",
                    type=NotificationType.ACTIVITY,
                    family_id=user.family_id,
                    actor_user_id=user.id,
                    metadata_payload={
                        "goal_id": str(goal.id),
                        "contribution_id": str(contribution.id),
                        "transaction_type": data.transaction_type,
                        "amount": float(amount)
                    }
                )
            )
            
            self.db.commit()
            
            # Reload relationships to populate properties in Pydantic schema
            stmt = select(GoalContribution).options(
                selectinload(GoalContribution.contributor),
                selectinload(GoalContribution.wallet)
            ).where(GoalContribution.id == contribution.id)
            return self.db.execute(stmt).scalar_one()
        except Exception as e:
            self.db.rollback()
            raise e

    def get_family_goals(self, user: User) -> list[Goal]:
        stmt = select(Goal).where(Goal.family_id == user.family_id).order_by(Goal.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def get_goal_detail(self, user: User, goal_id: UUID) -> Goal:
        stmt = (
            select(Goal)
            .options(
                selectinload(Goal.contributions).selectinload(GoalContribution.contributor),
                selectinload(Goal.contributions).selectinload(GoalContribution.wallet)
            )
            .where(Goal.id == goal_id, Goal.family_id == user.family_id)
        )
        goal = self.db.execute(stmt).scalar_one_or_none()
        if not goal:
            raise HTTPException(status_code=404, detail="Goal tidak ditemukan")
        
        goal.contributions.sort(key=lambda x: x.contribution_date, reverse=True)
        return goal

    def delete_goal(self, user: User, goal_id: UUID) -> str:
        goal = self._lock_goal(goal_id, user.family_id)
        
        # Fetch all contributions
        stmt = select(GoalContribution).where(GoalContribution.goal_id == goal.id)
        contributions = list(self.db.execute(stmt).scalars().all())
        
        # Lock wallets in sorted order to prevent deadlocks
        wallet_ids = list(set(c.wallet_id for c in contributions if c.wallet_id is not None))
        wallet_ids.sort()
        
        wallets = {}
        for wid in wallet_ids:
            wallets[wid] = self._lock_wallet(wid, user.family_id)
            
        for c in contributions:
            if c.wallet_id and c.transaction_id:
                wallet = wallets[c.wallet_id]
                amount = Decimal(str(c.amount))
                if c.transaction_type == "DEPOSIT":
                    wallet.balance = Decimal(str(wallet.balance)) + amount
                else:
                    new_balance = Decimal(str(wallet.balance)) - amount
                    if new_balance < 0:
                        self.db.rollback()
                        raise HTTPException(status_code=400, detail="Reversal failed: Saldo wallet tidak mencukupi")
                    wallet.balance = new_balance
                
                # Delete associated transaction
                txn = self.db.execute(select(Transaction).where(Transaction.id == c.transaction_id)).scalar_one_or_none()
                if txn:
                    self.db.delete(txn)
                    
        try:
            # Cascade will delete GoalContributions
            self.db.delete(goal)
            self.db.flush()
            
            from app.services.notification_service import NotificationService
            from app.schemas.notification import NotificationCreate
            from app.models.notification import NotificationType
            NotificationService.create_notification(
                self.db,
                NotificationCreate(
                    title="Goal Dihapus",
                    message=f"Goal '{goal.name}' telah dihapus permanen.",
                    type=NotificationType.ACTIVITY,
                    family_id=user.family_id,
                    actor_user_id=user.id,
                    metadata_payload={
                        "goal_id": str(goal.id),
                        "name": goal.name
                    }
                )
            )
            
            self.db.commit()
            return "Goal berhasil dihapus"
        except Exception as e:
            self.db.rollback()
            raise e
