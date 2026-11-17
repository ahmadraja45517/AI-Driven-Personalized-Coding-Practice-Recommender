from sqlalchemy.dialects import postgresql
"""seed reference data: topics + sections

Revision ID: 0002_seed
Revises: 0001_initial
"""
import sqlalchemy as sa
from alembic import op

revision = "0002_seed"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

TOPICS = [
    # (code, name, is_diagnostic_topic, order_index)
    ("fundamentals",      "Programming Fundamentals", False, 1),
    ("arrays",            "Arrays",                   True,  2),
    ("strings",           "Strings",                  True,  3),
    ("searching_sorting", "Searching and Sorting",    True,  4),
    ("linked_lists",      "Linked Lists",             True,  5),
    ("stacks_queues",     "Stacks and Queues",        False, 6),
    ("recursion",         "Recursion",                True,  7),
    ("trees",             "Trees",                    True,  8),
    ("graphs",            "Graphs",                   False, 9),
    ("dynamic_programming", "Dynamic Programming",    True, 10),
]

SECTIONS = [
    # (slug, title, topic_code, order_index, content_status)
    ("fundamentals",  "Programming Fundamentals", "fundamentals",      1, "PUBLISHED"),
    ("arrays",        "Arrays",                   "arrays",            2, "PUBLISHED"),
    ("strings",       "Strings",                  "strings",           3, "PUBLISHED"),
    ("linked-lists",  "Linked Lists",             "linked_lists",      4, "PLANNED"),
    ("stacks-queues", "Stacks and Queues",        "stacks_queues",     5, "PLANNED"),
    ("trees",         "Trees and Binary Trees",   "trees",             6, "PLANNED"),
    ("graphs",        "Graphs",                   "graphs",            7, "PLANNED"),
    ("dynamic-programming", "Dynamic Programming", "dynamic_programming", 8, "PLANNED"),
]


def upgrade() -> None:
    topics_tbl = sa.table(
        "topics",
        sa.column("code", sa.String), sa.column("name", sa.String),
        sa.column("is_diagnostic_topic", sa.Boolean), sa.column("order_index", sa.SmallInteger),
    )
    op.bulk_insert(topics_tbl, [
        {"code": c, "name": n, "is_diagnostic_topic": d, "order_index": i}
        for c, n, d, i in TOPICS
    ])

    bind = op.get_bind()
    topic_ids = dict(bind.execute(sa.text("SELECT code, id FROM topics")).all())

    sections_tbl = sa.table(
    "learning_sections",
    sa.column("slug", sa.String),
    sa.column("title", sa.String),
    sa.column("topic_id", sa.BigInteger),
    sa.column("order_index", sa.SmallInteger),
    sa.column("content_status",
              postgresql.ENUM(name="section_content_status", create_type=False)),
    sa.column("target_level",
              postgresql.ENUM(name="student_level", create_type=False)),
)
    op.bulk_insert(sections_tbl, [
        {
            "slug": slug, "title": title, "topic_id": topic_ids[tc],
            "order_index": order, "content_status": status, "target_level": "BEGINNER",
        }
        for slug, title, tc, order, status in SECTIONS
    ])


def downgrade() -> None:
    op.execute("DELETE FROM learning_sections")
    op.execute("DELETE FROM topics")