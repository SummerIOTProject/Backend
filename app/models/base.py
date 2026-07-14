from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column


BIGINT_PK = BigInteger().with_variant(Integer, "sqlite")


class TimestampedModel:
    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
