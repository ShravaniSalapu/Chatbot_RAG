"""007_chatbot_documents"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "36eedb9ac854"
down_revision = "1603f42c7c06"
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        "chatbot_documents",

        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "chatbot_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "document_id",
            sa.String(length=36),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),

        sa.ForeignKeyConstraint(
            ["chatbot_id"],
            ["chatbots.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_chatbot_documents_chatbot_id",
        "chatbot_documents",
        ["chatbot_id"],
    )

    op.create_index(
        "ix_chatbot_documents_document_id",
        "chatbot_documents",
        ["document_id"],
    )


def downgrade():

    op.drop_index(
        "ix_chatbot_documents_document_id",
        table_name="chatbot_documents",
    )

    op.drop_index(
        "ix_chatbot_documents_chatbot_id",
        table_name="chatbot_documents",
    )

    op.drop_table("chatbot_documents")