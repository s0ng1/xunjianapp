from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.assets.models import Asset, AssetCredential


class AssetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, asset_id: int) -> Asset | None:
        return await self.session.get(Asset, asset_id)

    async def get_by_ip(self, ip: str) -> Asset | None:
        result = await self.session.execute(select(Asset).where(Asset.ip == ip))
        return result.scalar_one_or_none()

    async def list_all(self, *, skip: int = 0, limit: int = 100) -> list[Asset]:
        result = await self.session.execute(
            select(Asset).order_by(Asset.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def add(
        self,
        *,
        ip: str,
        asset_type: str,
        name: str,
        connection_type: str,
        port: int,
        username: str | None,
        vendor: str | None,
        credential_id: int | None,
        is_enabled: bool,
    ) -> Asset:
        asset = Asset(
            ip=ip,
            asset_type=asset_type,
            name=name,
            connection_type=connection_type,
            port=port,
            username=username,
            vendor=vendor,
            credential_id=credential_id,
            is_enabled=is_enabled,
        )
        self.session.add(asset)
        await self.session.flush()
        await self.session.refresh(asset)
        return asset

    async def delete(self, asset: Asset) -> None:
        await self.session.delete(asset)

    async def save(self, asset: Asset) -> Asset:
        await self.session.flush()
        await self.session.refresh(asset)
        return asset

    async def count_by_credential_id(self, credential_id: int, *, exclude_asset_id: int | None = None) -> int:
        statement = select(func.count()).select_from(Asset).where(Asset.credential_id == credential_id)
        if exclude_asset_id is not None:
            statement = statement.where(Asset.id != exclude_asset_id)
        result = await self.session.execute(statement)
        return int(result.scalar_one())


class AssetCredentialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, *, encrypted_password: str) -> AssetCredential:
        credential = AssetCredential(encrypted_password=encrypted_password)
        self.session.add(credential)
        await self.session.flush()
        await self.session.refresh(credential)
        return credential

    async def get_by_id(self, credential_id: int) -> AssetCredential | None:
        return await self.session.get(AssetCredential, credential_id)

    async def save(self, credential: AssetCredential) -> AssetCredential:
        await self.session.flush()
        await self.session.refresh(credential)
        return credential

    async def delete(self, credential: AssetCredential) -> None:
        await self.session.delete(credential)
