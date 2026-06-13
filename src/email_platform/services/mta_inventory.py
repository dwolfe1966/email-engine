from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from email_platform.models.entities import (
    MtaIpPool,
    MtaIpPoolNode,
    MtaNode,
    MtaOperationalStatus,
    MtaProviderAccount,
)
from email_platform.schemas.contracts import (
    MtaIpPoolCreate,
    MtaIpPoolNodeCreate,
    MtaIpPoolNodeUpdate,
    MtaIpPoolUpdate,
    MtaNodeCreate,
    MtaNodeUpdate,
    MtaProviderAccountCreate,
    MtaProviderAccountUpdate,
)


class MtaInventoryError(ValueError):
    pass


class MtaInventoryService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_provider_account(self, payload: MtaProviderAccountCreate) -> MtaProviderAccount:
        account = MtaProviderAccount(**payload.model_dump())
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def get_provider_account(self, account_id: UUID) -> MtaProviderAccount | None:
        return self.db.get(MtaProviderAccount, account_id)

    def list_provider_accounts(
        self,
        status: MtaOperationalStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MtaProviderAccount]:
        statement = select(MtaProviderAccount).order_by(
            MtaProviderAccount.created_at.desc(),
        )
        if status:
            statement = statement.where(MtaProviderAccount.status == status)
        return list(self.db.scalars(statement.limit(limit).offset(offset)).all())

    def count_provider_accounts(self, status: MtaOperationalStatus | None = None) -> int:
        statement = select(func.count()).select_from(MtaProviderAccount)
        if status:
            statement = statement.where(MtaProviderAccount.status == status)
        return int(self.db.scalar(statement) or 0)

    def update_provider_account(
        self,
        account_id: UUID,
        payload: MtaProviderAccountUpdate,
    ) -> MtaProviderAccount | None:
        account = self.get_provider_account(account_id)
        if not account:
            return None
        self._apply(account, payload.model_dump(exclude_unset=True))
        return self._commit_refresh(account)

    def set_provider_account_status(
        self,
        account_id: UUID,
        status: MtaOperationalStatus,
    ) -> MtaProviderAccount | None:
        account = self.get_provider_account(account_id)
        if not account:
            return None
        account.status = status
        return self._commit_refresh(account)

    def create_node(self, payload: MtaNodeCreate) -> MtaNode:
        self._require_provider_account(payload.provider_account_id)
        node = MtaNode(**payload.model_dump())
        self.db.add(node)
        self.db.commit()
        self.db.refresh(node)
        return node

    def get_node(self, node_id: UUID) -> MtaNode | None:
        return self.db.get(MtaNode, node_id)

    def list_nodes(
        self,
        status: MtaOperationalStatus | None = None,
        provider_account_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MtaNode]:
        statement = select(MtaNode).order_by(MtaNode.created_at.desc())
        if status:
            statement = statement.where(MtaNode.status == status)
        if provider_account_id:
            statement = statement.where(MtaNode.provider_account_id == provider_account_id)
        return list(self.db.scalars(statement.limit(limit).offset(offset)).all())

    def count_nodes(
        self,
        status: MtaOperationalStatus | None = None,
        provider_account_id: UUID | None = None,
    ) -> int:
        statement = select(func.count()).select_from(MtaNode)
        if status:
            statement = statement.where(MtaNode.status == status)
        if provider_account_id:
            statement = statement.where(MtaNode.provider_account_id == provider_account_id)
        return int(self.db.scalar(statement) or 0)

    def update_node(self, node_id: UUID, payload: MtaNodeUpdate) -> MtaNode | None:
        node = self.get_node(node_id)
        if not node:
            return None
        updates = payload.model_dump(exclude_unset=True)
        provider_account_id = updates.get('provider_account_id')
        if provider_account_id:
            self._require_provider_account(provider_account_id)
        self._apply(node, updates)
        return self._commit_refresh(node)

    def set_node_status(self, node_id: UUID, status: MtaOperationalStatus) -> MtaNode | None:
        node = self.get_node(node_id)
        if not node:
            return None
        node.status = status
        return self._commit_refresh(node)

    def create_ip_pool(self, payload: MtaIpPoolCreate) -> MtaIpPool:
        pool = MtaIpPool(**payload.model_dump())
        self.db.add(pool)
        self.db.commit()
        self.db.refresh(pool)
        return pool

    def get_ip_pool(self, pool_id: UUID) -> MtaIpPool | None:
        return self.db.get(MtaIpPool, pool_id)

    def list_ip_pools(
        self,
        status: MtaOperationalStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MtaIpPool]:
        statement = select(MtaIpPool).order_by(MtaIpPool.created_at.desc())
        if status:
            statement = statement.where(MtaIpPool.status == status)
        return list(self.db.scalars(statement.limit(limit).offset(offset)).all())

    def count_ip_pools(self, status: MtaOperationalStatus | None = None) -> int:
        statement = select(func.count()).select_from(MtaIpPool)
        if status:
            statement = statement.where(MtaIpPool.status == status)
        return int(self.db.scalar(statement) or 0)

    def update_ip_pool(self, pool_id: UUID, payload: MtaIpPoolUpdate) -> MtaIpPool | None:
        pool = self.get_ip_pool(pool_id)
        if not pool:
            return None
        self._apply(pool, payload.model_dump(exclude_unset=True))
        return self._commit_refresh(pool)

    def set_ip_pool_status(self, pool_id: UUID, status: MtaOperationalStatus) -> MtaIpPool | None:
        pool = self.get_ip_pool(pool_id)
        if not pool:
            return None
        pool.status = status
        return self._commit_refresh(pool)

    def create_pool_node(self, payload: MtaIpPoolNodeCreate) -> MtaIpPoolNode:
        self._require_ip_pool(payload.ip_pool_id)
        self._require_node(payload.mta_node_id)
        pool_node = MtaIpPoolNode(**payload.model_dump())
        self.db.add(pool_node)
        self.db.commit()
        self.db.refresh(pool_node)
        return pool_node

    def get_pool_node(self, pool_node_id: UUID) -> MtaIpPoolNode | None:
        return self.db.get(MtaIpPoolNode, pool_node_id)

    def list_pool_nodes(
        self,
        ip_pool_id: UUID | None = None,
        mta_node_id: UUID | None = None,
        status: MtaOperationalStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MtaIpPoolNode]:
        statement = select(MtaIpPoolNode).order_by(
            MtaIpPoolNode.priority.asc(),
            MtaIpPoolNode.created_at.desc(),
        )
        if ip_pool_id:
            statement = statement.where(MtaIpPoolNode.ip_pool_id == ip_pool_id)
        if mta_node_id:
            statement = statement.where(MtaIpPoolNode.mta_node_id == mta_node_id)
        if status:
            statement = statement.where(MtaIpPoolNode.status == status)
        return list(self.db.scalars(statement.limit(limit).offset(offset)).all())

    def count_pool_nodes(
        self,
        ip_pool_id: UUID | None = None,
        mta_node_id: UUID | None = None,
        status: MtaOperationalStatus | None = None,
    ) -> int:
        statement = select(func.count()).select_from(MtaIpPoolNode)
        if ip_pool_id:
            statement = statement.where(MtaIpPoolNode.ip_pool_id == ip_pool_id)
        if mta_node_id:
            statement = statement.where(MtaIpPoolNode.mta_node_id == mta_node_id)
        if status:
            statement = statement.where(MtaIpPoolNode.status == status)
        return int(self.db.scalar(statement) or 0)

    def update_pool_node(
        self,
        pool_node_id: UUID,
        payload: MtaIpPoolNodeUpdate,
    ) -> MtaIpPoolNode | None:
        pool_node = self.get_pool_node(pool_node_id)
        if not pool_node:
            return None
        self._apply(pool_node, payload.model_dump(exclude_unset=True))
        return self._commit_refresh(pool_node)

    def set_pool_node_status(
        self,
        pool_node_id: UUID,
        status: MtaOperationalStatus,
    ) -> MtaIpPoolNode | None:
        pool_node = self.get_pool_node(pool_node_id)
        if not pool_node:
            return None
        pool_node.status = status
        return self._commit_refresh(pool_node)

    def _require_provider_account(self, account_id: UUID) -> MtaProviderAccount:
        account = self.get_provider_account(account_id)
        if not account:
            raise MtaInventoryError('MTA provider account not found')
        return account

    def _require_node(self, node_id: UUID) -> MtaNode:
        node = self.get_node(node_id)
        if not node:
            raise MtaInventoryError('MTA node not found')
        return node

    def _require_ip_pool(self, pool_id: UUID) -> MtaIpPool:
        pool = self.get_ip_pool(pool_id)
        if not pool:
            raise MtaInventoryError('MTA IP pool not found')
        return pool

    def _commit_refresh(self, item):
        self.db.commit()
        self.db.refresh(item)
        return item

    @staticmethod
    def _apply(item, updates: dict[str, object]) -> None:
        for key, value in updates.items():
            setattr(item, key, value)
