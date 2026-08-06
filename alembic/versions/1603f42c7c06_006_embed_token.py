"""006_embed_token

Revision ID: 1603f42c7c06
Revises: dc1b80238cde
Create Date: 2026-08-06 23:47:30.362465

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import uuid
from sqlalchemy.sql import text



# revision identifiers, used by Alembic.
revision: str = '1603f42c7c06'
down_revision: Union[str, None] = 'dc1b80238cde'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from sqlalchemy.sql import text
import uuid


def upgrade() -> None:
    op.add_column(
        "chatbots",
        sa.Column("embed_token", sa.String(length=64), nullable=True),
    )

    conn = op.get_bind()

    rows = conn.execute(text("SELECT id FROM chatbots")).fetchall()

    for row in rows:
        conn.execute(
            text(
                "UPDATE chatbots "
                "SET embed_token = :token "
                "WHERE id = :id"
            ),
            {
                "token": uuid.uuid4().hex,
                "id": row.id,
            },
        )

    op.alter_column(
        "chatbots",
        "embed_token",
        nullable=False,
    )

    op.create_unique_constraint(
        "uq_chatbots_embed_token",
        "chatbots",
        ["embed_token"],
    )

def downgrade() -> None:
    op.drop_constraint(
        "uq_chatbots_embed_token",
        "chatbots",
        type_="unique",
    )
    op.drop_column("chatbots", "embed_token")