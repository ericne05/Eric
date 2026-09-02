"""
SQLite Knowledge Graph Store.
Provides fast persistent graph database storage for Nodes and Edges using SQLite.
"""

import json, sqlite3
from typing import Any, Dict, List, Optional

from core.knowledge.enums import KnowledgeNodeType, KnowledgeRelationType
from core.knowledge.interfaces import IKnowledgeGraphStore
from core.knowledge.models import KnowledgeEdge, KnowledgeGraph, KnowledgeNode


class SQLiteKnowledgeGraphStore(IKnowledgeGraphStore):
    """
    SQLite-backed Knowledge & Experience Graph Storage.
    Supports in-memory (:memory:) or file-based SQLite database.
    """

    def __init__(self, db_path: str = ":memory:"):
        self._db_path = db_path
        self._conn = sqlite3.connect(self._db_path)
        self._create_tables()

    def _create_tables(self) -> None:
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    attributes TEXT,
                    usage_count INTEGER,
                    success_rate REAL,
                    experience_score REAL,
                    created_at TEXT
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    confidence REAL,
                    weight REAL,
                    attributes TEXT,
                    created_at TEXT
                )
            """)

    def save_node(self, node: KnowledgeNode) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO nodes (id, node_type, name, attributes, usage_count, success_rate, experience_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    attributes=excluded.attributes,
                    usage_count=excluded.usage_count,
                    success_rate=excluded.success_rate,
                    experience_score=excluded.experience_score
            """,
                (
                    node.id,
                    node.node_type.value,
                    node.name,
                    json.dumps(node.attributes),
                    node.usage_count,
                    node.success_rate,
                    node.experience_score,
                    node.created_at.isoformat(),
                ),
            )

    def save_edge(self, edge: KnowledgeEdge) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO edges (id, source_id, target_id, relation_type, confidence, weight, attributes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    confidence=excluded.confidence,
                    weight=excluded.weight,
                    attributes=excluded.attributes
            """,
                (
                    edge.id,
                    edge.source_id,
                    edge.target_id,
                    edge.relation_type.value,
                    edge.confidence,
                    edge.weight,
                    json.dumps(edge.attributes),
                    edge.created_at.isoformat(),
                ),
            )

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT id, node_type, name, attributes, usage_count, success_rate, experience_score FROM nodes WHERE id = ?", (node_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return KnowledgeNode(
            id=row[0],
            node_type=KnowledgeNodeType(row[1]),
            name=row[2],
            attributes=json.loads(row[3] or "{}"),
            usage_count=row[4],
            success_rate=row[5],
            experience_score=row[6],
        )

    def query_nodes(self, node_type: KnowledgeNodeType) -> List[KnowledgeNode]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT id, node_type, name, attributes, usage_count, success_rate, experience_score FROM nodes WHERE node_type = ?", (node_type.value,))
        rows = cursor.fetchall()
        return [
            KnowledgeNode(
                id=r[0],
                node_type=KnowledgeNodeType(r[1]),
                name=r[2],
                attributes=json.loads(r[3] or "{}"),
                usage_count=r[4],
                success_rate=r[5],
                experience_score=r[6],
            )
            for r in rows
        ]

    def get_graph(self) -> KnowledgeGraph:
        graph = KnowledgeGraph()
        cursor = self._conn.cursor()

        cursor.execute("SELECT id, node_type, name, attributes, usage_count, success_rate, experience_score FROM nodes")
        for r in cursor.fetchall():
            node = KnowledgeNode(
                id=r[0],
                node_type=KnowledgeNodeType(r[1]),
                name=r[2],
                attributes=json.loads(r[3] or "{}"),
                usage_count=r[4],
                success_rate=r[5],
                experience_score=r[6],
            )
            graph.add_node(node)

        cursor.execute("SELECT id, source_id, target_id, relation_type, confidence, weight, attributes FROM edges")
        for r in cursor.fetchall():
            edge = KnowledgeEdge(
                id=r[0],
                source_id=r[1],
                target_id=r[2],
                relation_type=KnowledgeRelationType(r[3]),
                confidence=r[4],
                weight=r[5],
                attributes=json.loads(r[6] or "{}"),
            )
            graph.edges.append(edge)

        return graph

    def clear(self) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM nodes")
            self._conn.execute("DELETE FROM edges")
