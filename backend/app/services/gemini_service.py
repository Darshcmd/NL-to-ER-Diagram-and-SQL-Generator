"""Rule-based schema generation service.

The original project depended on hard-coded placeholders. This service now
implements a deterministic multi-stage pipeline that can run without an API key:

Input -> entity extraction -> clarification questions -> schema blueprint ->
Chen ER diagram -> SQL DDL -> validation notes.
"""

from __future__ import annotations

import logging
import json
import re
from collections import Counter, OrderedDict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from app.models.schema import (
    ClarifyingQuestion,
    CurrentSchema,
    SchemaAttribute,
    SchemaEntity,
    SchemaRelationship,
)

logger = logging.getLogger(__name__)


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "for",
    "from",
    "have",
    "has",
    "how",
    "in",
    "include",
    "includes",
    "into",
    "is",
    "it",
    "may",
    "need",
    "needs",
    "of",
    "on",
    "or",
    "our",
    "should",
    "store",
    "stores",
    "the",
    "their",
    "there",
    "this",
    "to",
    "track",
    "tracks",
    "with",
    "within",
    "will",
    "would",
    "you",
    "your",
}

ENTITY_ALIASES = {
    "buyer": "customer",
    "client": "customer",
    "customer": "customer",
    "users": "customer",
    "user": "customer",
    "account": "account",
    "accounts": "account",
    "product": "product",
    "products": "product",
    "item": "item",
    "items": "item",
    "order": "order",
    "orders": "order",
    "orderitem": "order_item",
    "order_item": "order_item",
    "lineitem": "order_item",
    "line_item": "order_item",
    "category": "category",
    "categories": "category",
    "payment": "payment",
    "payments": "payment",
    "shipment": "shipment",
    "shipments": "shipment",
    "address": "address",
    "addresses": "address",
    "cart": "cart",
    "carts": "cart",
    "review": "review",
    "reviews": "review",
    "discount": "promotion",
    "coupon": "promotion",
    "promotion": "promotion",
    "student": "student",
    "students": "student",
    "teacher": "instructor",
    "instructor": "instructor",
    "course": "course",
    "courses": "course",
    "enrollment": "enrollment",
    "enrollments": "enrollment",
    "assignment": "assignment",
    "assignments": "assignment",
    "grade": "grade",
    "grades": "grade",
    "patient": "patient",
    "patients": "patient",
    "doctor": "doctor",
    "doctors": "doctor",
    "appointment": "appointment",
    "appointments": "appointment",
    "prescription": "prescription",
    "prescriptions": "prescription",
    "medication": "medication",
    "medications": "medication",
    "visit": "visit",
    "visits": "visit",
    "employee": "employee",
    "employees": "employee",
    "project": "project",
    "projects": "project",
    "task": "task",
    "tasks": "task",
}

TYPE_ALIASES = {
    "int": "int",
    "integer": "int",
    "bigint": "bigint",
    "serial": "int",
    "uuid": "uuid",
    "string": "string",
    "text": "text",
    "varchar": "string",
    "char": "string",
    "boolean": "boolean",
    "bool": "boolean",
    "date": "date",
    "time": "timestamp",
    "timestamp": "timestamp",
    "datetime": "timestamp",
    "decimal": "decimal",
    "numeric": "decimal",
    "float": "decimal",
    "double": "decimal",
}

ENTITY_TEMPLATES: Dict[str, List[SchemaAttribute]] = {
    "actor": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="name", type="string", nullable=False),
        SchemaAttribute(name="email", type="string", unique=True),
        SchemaAttribute(name="created_at", type="timestamp", default="CURRENT_TIMESTAMP"),
    ],
    "record": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="title", type="string", nullable=False),
        SchemaAttribute(name="description", type="text"),
        SchemaAttribute(name="status", type="string", default="'draft'"),
        SchemaAttribute(name="created_at", type="timestamp", default="CURRENT_TIMESTAMP"),
    ],
    "transaction": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="actor_id", type="int", fk=True, nullable=False),
        SchemaAttribute(name="record_id", type="int", fk=True, nullable=False),
        SchemaAttribute(name="action_type", type="string", nullable=False),
        SchemaAttribute(name="status", type="string", default="'pending'"),
        SchemaAttribute(name="created_at", type="timestamp", default="CURRENT_TIMESTAMP"),
    ],
    "reference": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="transaction_id", type="int", fk=True, nullable=False),
        SchemaAttribute(name="reference_code", type="string", unique=True),
        SchemaAttribute(name="created_at", type="timestamp", default="CURRENT_TIMESTAMP"),
    ],
    "customer": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="full_name", type="string", nullable=False),
        SchemaAttribute(name="email", type="string", nullable=False, unique=True),
        SchemaAttribute(name="phone", type="string"),
        SchemaAttribute(name="created_at", type="timestamp", default="CURRENT_TIMESTAMP"),
        SchemaAttribute(name="updated_at", type="timestamp", default="CURRENT_TIMESTAMP"),
    ],
    "account": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="email", type="string", nullable=False, unique=True),
        SchemaAttribute(name="password_hash", type="string", nullable=False),
        SchemaAttribute(name="role", type="string", nullable=False, default="'member'"),
        SchemaAttribute(name="created_at", type="timestamp", default="CURRENT_TIMESTAMP"),
    ],
    "product": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="sku", type="string", nullable=False, unique=True),
        SchemaAttribute(name="name", type="string", nullable=False),
        SchemaAttribute(name="description", type="text"),
        SchemaAttribute(name="price", type="decimal", nullable=False),
        SchemaAttribute(name="stock_quantity", type="int", default="0"),
        SchemaAttribute(name="created_at", type="timestamp", default="CURRENT_TIMESTAMP"),
        SchemaAttribute(name="updated_at", type="timestamp", default="CURRENT_TIMESTAMP"),
    ],
    "order": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="order_number", type="string", nullable=False, unique=True),
        SchemaAttribute(name="status", type="string", nullable=False, default="'pending'"),
        SchemaAttribute(name="total_amount", type="decimal", nullable=False, default="0"),
        SchemaAttribute(name="ordered_at", type="timestamp", default="CURRENT_TIMESTAMP"),
        SchemaAttribute(name="created_at", type="timestamp", default="CURRENT_TIMESTAMP"),
        SchemaAttribute(name="updated_at", type="timestamp", default="CURRENT_TIMESTAMP"),
    ],
    "order_item": [
        SchemaAttribute(name="order_id", type="int", pk=True, fk=True, nullable=False),
        SchemaAttribute(name="product_id", type="int", pk=True, fk=True, nullable=False),
        SchemaAttribute(name="quantity", type="int", nullable=False, default="1"),
        SchemaAttribute(name="unit_price", type="decimal", nullable=False),
        SchemaAttribute(name="line_total", type="decimal"),
    ],
    "category": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="name", type="string", nullable=False, unique=True),
        SchemaAttribute(name="description", type="text"),
    ],
    "payment": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="payment_reference", type="string", nullable=False, unique=True),
        SchemaAttribute(name="amount", type="decimal", nullable=False),
        SchemaAttribute(name="method", type="string", nullable=False),
        SchemaAttribute(name="status", type="string", nullable=False, default="'initiated'"),
        SchemaAttribute(name="processed_at", type="timestamp"),
    ],
    "shipment": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="tracking_number", type="string", unique=True),
        SchemaAttribute(name="carrier", type="string"),
        SchemaAttribute(name="status", type="string", nullable=False, default="'pending'"),
        SchemaAttribute(name="shipped_at", type="timestamp"),
        SchemaAttribute(name="delivered_at", type="timestamp"),
    ],
    "address": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="street", type="string", nullable=False),
        SchemaAttribute(name="city", type="string", nullable=False),
        SchemaAttribute(name="state", type="string"),
        SchemaAttribute(name="postal_code", type="string"),
        SchemaAttribute(name="country", type="string", default="'United States'"),
    ],
    "cart": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="cart_number", type="string", unique=True),
        SchemaAttribute(name="status", type="string", default="'active'"),
        SchemaAttribute(name="created_at", type="timestamp", default="CURRENT_TIMESTAMP"),
    ],
    "review": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="rating", type="int", nullable=False),
        SchemaAttribute(name="review_text", type="text"),
        SchemaAttribute(name="created_at", type="timestamp", default="CURRENT_TIMESTAMP"),
    ],
    "promotion": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="code", type="string", nullable=False, unique=True),
        SchemaAttribute(name="discount_type", type="string", nullable=False),
        SchemaAttribute(name="discount_value", type="decimal", nullable=False),
        SchemaAttribute(name="starts_at", type="timestamp"),
        SchemaAttribute(name="ends_at", type="timestamp"),
    ],
    "student": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="student_number", type="string", nullable=False, unique=True),
        SchemaAttribute(name="full_name", type="string", nullable=False),
        SchemaAttribute(name="email", type="string", unique=True),
        SchemaAttribute(name="created_at", type="timestamp", default="CURRENT_TIMESTAMP"),
    ],
    "instructor": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="employee_number", type="string", unique=True),
        SchemaAttribute(name="full_name", type="string", nullable=False),
        SchemaAttribute(name="email", type="string", unique=True),
    ],
    "course": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="course_code", type="string", nullable=False, unique=True),
        SchemaAttribute(name="title", type="string", nullable=False),
        SchemaAttribute(name="description", type="text"),
        SchemaAttribute(name="credits", type="int", default="3"),
    ],
    "enrollment": [
        SchemaAttribute(name="student_id", type="int", pk=True, fk=True, nullable=False),
        SchemaAttribute(name="course_id", type="int", pk=True, fk=True, nullable=False),
        SchemaAttribute(name="enrolled_at", type="timestamp", default="CURRENT_TIMESTAMP"),
        SchemaAttribute(name="status", type="string", default="'active'"),
        SchemaAttribute(name="grade", type="string"),
    ],
    "assignment": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="title", type="string", nullable=False),
        SchemaAttribute(name="description", type="text"),
        SchemaAttribute(name="due_date", type="date"),
        SchemaAttribute(name="max_score", type="decimal"),
    ],
    "grade": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="score", type="decimal", nullable=False),
        SchemaAttribute(name="graded_at", type="timestamp", default="CURRENT_TIMESTAMP"),
    ],
    "patient": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="medical_record_number", type="string", nullable=False, unique=True),
        SchemaAttribute(name="full_name", type="string", nullable=False),
        SchemaAttribute(name="date_of_birth", type="date"),
        SchemaAttribute(name="phone", type="string"),
    ],
    "doctor": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="license_number", type="string", nullable=False, unique=True),
        SchemaAttribute(name="full_name", type="string", nullable=False),
        SchemaAttribute(name="specialty", type="string"),
        SchemaAttribute(name="email", type="string", unique=True),
    ],
    "appointment": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="scheduled_at", type="timestamp", nullable=False),
        SchemaAttribute(name="status", type="string", default="'scheduled'"),
        SchemaAttribute(name="reason", type="text"),
    ],
    "prescription": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="medication_name", type="string", nullable=False),
        SchemaAttribute(name="dosage", type="string"),
        SchemaAttribute(name="frequency", type="string"),
        SchemaAttribute(name="prescribed_at", type="timestamp", default="CURRENT_TIMESTAMP"),
    ],
    "medication": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="name", type="string", nullable=False, unique=True),
        SchemaAttribute(name="description", type="text"),
    ],
    "visit": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="visited_at", type="timestamp", nullable=False),
        SchemaAttribute(name="notes", type="text"),
    ],
    "employee": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="employee_number", type="string", nullable=False, unique=True),
        SchemaAttribute(name="full_name", type="string", nullable=False),
        SchemaAttribute(name="email", type="string", unique=True),
        SchemaAttribute(name="role", type="string"),
        SchemaAttribute(name="created_at", type="timestamp", default="CURRENT_TIMESTAMP"),
    ],
    "project": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="project_code", type="string", nullable=False, unique=True),
        SchemaAttribute(name="name", type="string", nullable=False),
        SchemaAttribute(name="description", type="text"),
        SchemaAttribute(name="started_at", type="timestamp"),
        SchemaAttribute(name="ended_at", type="timestamp"),
    ],
    "task": [
        SchemaAttribute(name="id", type="int", pk=True, nullable=False),
        SchemaAttribute(name="title", type="string", nullable=False),
        SchemaAttribute(name="description", type="text"),
        SchemaAttribute(name="status", type="string", default="'todo'"),
        SchemaAttribute(name="priority", type="string"),
        SchemaAttribute(name="due_date", type="date"),
    ],
}

DOMAIN_PROFILES = {
    "ecommerce": {
        "keywords": {
            "cart",
            "checkout",
            "coupon",
            "customer",
            "discount",
            "inventory",
            "order",
            "payment",
            "product",
            "purchase",
            "review",
            "shipping",
            "sku",
            "variant",
        },
        "base_entities": ["customer", "product", "order", "order_item", "category", "payment", "address"],
        "optional_entities": {
            "inventory": "product",
            "variant": "product_variant",
            "cart": "cart",
            "review": "review",
            "coupon": "promotion",
            "discount": "promotion",
            "promotion": "promotion",
            "shipment": "shipment",
            "shipping": "shipment",
        },
        "questions": [
            ("identity", "Should customers log in through a separate account table, or is customer identity enough?", "customer vs account", "Keep a dedicated account table with email and password hash."),
            ("m2m", "Should order items store quantity and unit price at purchase time?", "bridge table details", "Yes, keep an order_item bridge with quantity and unit_price."),
            ("catalog", "Do products need variants, inventory by variant, or just a single stock count?", "product structure", "Use product_variant and track inventory separately."),
            ("checkout", "Do you need payment, shipping, and billing address tables, or should those stay as simple order columns?", "fulfilment", "Model payments and shipments as separate entities."),
            ("constraints", "Which fields must stay unique, such as email, SKU, or order number?", "constraints", "Email and SKU should be unique."),
        ],
    },
    "education": {
        "keywords": {
            "assignment",
            "attendance",
            "class",
            "cohort",
            "course",
            "education",
            "enroll",
            "grade",
            "instructor",
            "lesson",
            "school",
            "semester",
            "student",
        },
        "base_entities": ["student", "course", "enrollment", "instructor", "assignment", "grade"],
        "optional_entities": {
            "department": "department",
            "schedule": "schedule",
            "attendance": "attendance",
            "prerequisite": "prerequisite",
            "exam": "exam",
            "cohort": "cohort",
        },
        "questions": [
            ("identity", "Should students and instructors each have their own login accounts, or are these just profile records?", "accounting", "Keep separate account and profile tables."),
            ("m2m", "Should course enrollment be a bridge table with enrolled_at, status, and grade fields?", "enrollment", "Yes, use an enrollment bridge table."),
            ("curriculum", "Do courses need prerequisites, credits, and department ownership?", "course rules", "Add a prerequisite table and a credits column."),
            ("assessment", "Should assignments and grades be stored per course, per student, or both?", "assessment flow", "Store assignments per course and grades per submission."),
            ("constraints", "Which identifiers must be unique, such as student number, course code, or instructor email?", "constraints", "Student number and course code should be unique."),
        ],
    },
    "healthcare": {
        "keywords": {
            "appointment",
            "billing",
            "clinic",
            "doctor",
            "hospital",
            "medication",
            "patient",
            "pharmacy",
            "prescription",
            "treatment",
            "visit",
        },
        "base_entities": ["patient", "doctor", "appointment", "prescription", "medication", "visit"],
        "optional_entities": {
            "billing": "billing_record",
            "invoice": "billing_record",
            "insurance": "insurance_policy",
            "lab": "lab_result",
            "report": "lab_result",
            "diagnosis": "diagnosis",
        },
        "questions": [
            ("identity", "Should patient identity be stored separately from portal logins and insurance details?", "identity and privacy", "Keep patient, account, and insurance records separate."),
            ("scheduling", "Do appointments need assigned doctor, location, duration, and status fields?", "scheduling", "Yes, appointments should carry scheduling metadata."),
            ("treatment", "Should prescriptions and visits be tracked as separate clinical events?", "clinical records", "Model visits, prescriptions, and diagnoses separately."),
            ("billing", "Do you need billing or insurance coverage tables, or is treatment data enough?", "billing", "Add billing and insurance entities if claims are required."),
            ("constraints", "Which fields must be unique, such as medical record number, license number, or prescription reference?", "constraints", "Medical record number and license number should be unique."),
        ],
    },
    "generic": {
        "keywords": set(),
        "base_entities": ["actor", "record", "transaction"],
        "optional_entities": {},
        "questions": [
            ("scope", "What are the core entities, and which one is the primary owner of the workflow?", "core entities", "Name the main tables and the owner record."),
            ("relationships", "Which relationships are one-to-many, and which are many-to-many?", "cardinality", "List the cardinality for each relationship."),
            ("identity", "Which fields must be unique or required for each entity?", "keys", "Use ids plus any business keys."),
            ("history", "Do you need timestamps, soft deletes, or audit history columns?", "lifecycle", "Add created_at and updated_at to transactional tables."),
            ("source", "If the input came from a document, should we preserve the source field names or normalize them?", "source mapping", "Normalize names for the final schema."),
        ],
    },
}

RELATIONSHIP_BLUEPRINTS = {
    "ecommerce": [
        ("customer", "order", "1:N", "places", None),
        ("order", "product", "M:N", "contains", "includes"),
        ("customer", "address", "1:N", "has", "belongs_to"),
        ("customer", "payment", "1:N", "makes", "belongs_to"),
        ("category", "product", "1:N", "categorizes", "belongs_to"),
        ("order", "shipment", "1:N", "ships_with", "fulfills"),
        ("customer", "cart", "1:N", "owns", "belongs_to"),
        ("cart", "product", "M:N", "contains", "appears_in"),
        ("product", "review", "1:N", "receives", "belongs_to"),
        ("promotion", "order", "1:N", "applies_to", "uses"),
    ],
    "education": [
        ("student", "course", "M:N", "enrolls_in", "has_students"),
        ("instructor", "course", "1:N", "teaches", "taught_by"),
        ("course", "assignment", "1:N", "has", "belongs_to"),
        ("student", "grade", "1:N", "earns", "belongs_to"),
        ("course", "cohort", "1:N", "runs_with", "belongs_to"),
    ],
    "healthcare": [
        ("patient", "appointment", "1:N", "books", "belongs_to"),
        ("doctor", "appointment", "1:N", "attends", "belongs_to"),
        ("patient", "prescription", "1:N", "receives", "belongs_to"),
        ("doctor", "prescription", "1:N", "writes", "belongs_to"),
        ("patient", "visit", "1:N", "has", "belongs_to"),
        ("visit", "diagnosis", "1:N", "records", "belongs_to"),
    ],
    "generic": [
        ("actor", "record", "1:N", "relates_to", "belongs_to"),
        ("actor", "transaction", "1:N", "initiates", "belongs_to"),
        ("record", "transaction", "1:N", "is_used_in", "references"),
    ],
}

BRIDGE_ENTITY_NAMES = {
    ("order", "product"): "order_item",
    ("cart", "product"): "cart_item",
    ("student", "course"): "enrollment",
    ("project", "employee"): "project_member",
}

BRIDGE_EXTRA_ATTRIBUTES = {
    "order_item": [
        SchemaAttribute(name="quantity", type="int", nullable=False, default="1"),
        SchemaAttribute(name="unit_price", type="decimal", nullable=False),
        SchemaAttribute(name="line_total", type="decimal"),
    ],
    "cart_item": [
        SchemaAttribute(name="quantity", type="int", nullable=False, default="1"),
    ],
    "enrollment": [
        SchemaAttribute(name="enrolled_at", type="timestamp", default="CURRENT_TIMESTAMP"),
        SchemaAttribute(name="status", type="string", default="'active'"),
        SchemaAttribute(name="grade", type="string"),
    ],
    "project_member": [
        SchemaAttribute(name="role", type="string"),
        SchemaAttribute(name="assigned_at", type="timestamp", default="CURRENT_TIMESTAMP"),
    ],
}

SQL_TYPE_MAP = {
    "postgresql": {
        "id": "SERIAL",
        "int": "INTEGER",
        "bigint": "BIGINT",
        "uuid": "UUID",
        "string": "VARCHAR(255)",
        "text": "TEXT",
        "boolean": "BOOLEAN",
        "date": "DATE",
        "timestamp": "TIMESTAMP",
        "decimal": "NUMERIC(12,2)",
    },
    "mysql": {
        "id": "INT AUTO_INCREMENT",
        "int": "INT",
        "bigint": "BIGINT",
        "uuid": "CHAR(36)",
        "string": "VARCHAR(255)",
        "text": "TEXT",
        "boolean": "BOOLEAN",
        "date": "DATE",
        "timestamp": "TIMESTAMP",
        "decimal": "DECIMAL(12,2)",
    },
    "sqlite": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "int": "INTEGER",
        "bigint": "INTEGER",
        "uuid": "TEXT",
        "string": "TEXT",
        "text": "TEXT",
        "boolean": "INTEGER",
        "date": "TEXT",
        "timestamp": "TEXT",
        "decimal": "NUMERIC",
    },
    "sqlserver": {
        "id": "INT IDENTITY(1,1)",
        "int": "INT",
        "bigint": "BIGINT",
        "uuid": "UNIQUEIDENTIFIER",
        "string": "NVARCHAR(255)",
        "text": "NVARCHAR(MAX)",
        "boolean": "BIT",
        "date": "DATE",
        "timestamp": "DATETIME2",
        "decimal": "DECIMAL(12,2)",
    },
    "oracle": {
        "id": "NUMBER GENERATED BY DEFAULT AS IDENTITY",
        "int": "NUMBER",
        "bigint": "NUMBER",
        "uuid": "RAW(16)",
        "string": "VARCHAR2(255)",
        "text": "CLOB",
        "boolean": "NUMBER(1)",
        "date": "DATE",
        "timestamp": "TIMESTAMP",
        "decimal": "NUMBER(12,2)",
    },
}


def _normalise_text(value: Optional[str]) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _extract_answer_context(text: Optional[str]) -> str:
    if not text:
        return ""

    answer_lines: List[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = re.match(r"^A\d+\s*:\s*(.+)$", line, re.IGNORECASE)
        if match:
            answer_lines.append(match.group(1).strip())

    return _normalise_text(" ".join(answer_lines)) if answer_lines else _normalise_text(text)


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9_]*", text.lower())


def _singularize(token: str) -> str:
    if token.endswith("ies") and len(token) > 3:
        return token[:-3] + "y"
    if token.endswith("ses") and len(token) > 4:
        return token[:-2]
    if token.endswith("xes") or token.endswith("zes") or token.endswith("ches") or token.endswith("shes"):
        return token[:-2]
    if token.endswith("s") and not token.endswith(("ss", "us")) and len(token) > 3:
        return token[:-1]
    return token


def _snake_case(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value.lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return _singularize(cleaned)


def _entity_label(value: str) -> str:
    return _snake_case(value).upper()


def _sql_table_name(entity_name: str) -> str:
    name = _snake_case(entity_name)
    if name in {"order", "customer", "product", "category", "payment", "address", "shipment", "account", "student", "course", "enrollment", "appointment", "prescription", "visit", "employee", "project", "task", "review", "promotion", "cart", "item"}:
        return {
            "order": "orders",
            "customer": "customers",
            "product": "products",
            "category": "categories",
            "payment": "payments",
            "address": "addresses",
            "shipment": "shipments",
            "account": "accounts",
            "student": "students",
            "course": "courses",
            "enrollment": "enrollments",
            "appointment": "appointments",
            "prescription": "prescriptions",
            "visit": "visits",
            "employee": "employees",
            "project": "projects",
            "task": "tasks",
            "review": "reviews",
            "promotion": "promotions",
            "cart": "carts",
            "item": "items",
        }[name]
    if name.endswith("y"):
        return f"{name[:-1]}ies"
    if name.endswith("s"):
        return f"{name}es"
    return f"{name}s"


def _capitalize_words(value: str) -> str:
    return " ".join(part.capitalize() for part in _snake_case(value).split("_") if part)


def _clone_attributes(attributes: Sequence[SchemaAttribute]) -> List[SchemaAttribute]:
    return [attr.model_copy(deep=True) for attr in attributes]


def _has_attribute(entity: SchemaEntity, attribute_name: str) -> bool:
    return any(attr.name == attribute_name for attr in entity.attributes)


def _append_if_missing(entity: SchemaEntity, attribute: SchemaAttribute) -> None:
    if not _has_attribute(entity, attribute.name):
        entity.attributes.append(attribute)


def _schema_payload(schema: CurrentSchema) -> Dict[str, object]:
    return {
        "domain": schema.domain,
        "summary": schema.summary,
        "validation_notes": list(schema.validation_notes),
        "sample_data": schema.sample_data,
        "entities": [
            {
                "name": entity.name,
                "label": entity.label,
                "description": entity.description,
                "attributes": [
                    {
                        "name": attribute.name,
                        "type": attribute.type,
                        "pk": attribute.pk,
                        "fk": attribute.fk,
                        "nullable": attribute.nullable,
                        "unique": attribute.unique,
                        "default": attribute.default,
                        "note": attribute.note,
                    }
                    for attribute in entity.attributes
                ],
            }
            for entity in schema.entities
        ],
        "relationships": [
            {
                "from_entity": relation.from_entity,
                "to_entity": relation.to_entity,
                "cardinality": relation.cardinality,
                "label": relation.label,
                "reverse_label": relation.reverse_label,
                "bridge_entity": relation.bridge_entity,
            }
            for relation in schema.relationships
        ],
    }


def _schema_from_payload(payload: Dict[str, object]) -> CurrentSchema:
    entities: List[SchemaEntity] = []
    for raw_entity in payload.get("entities", []) or []:
        entity_data = raw_entity or {}
        attributes = [
            SchemaAttribute(
                name=raw_attribute.get("name", ""),
                type=raw_attribute.get("type", "string"),
                pk=bool(raw_attribute.get("pk", False)),
                fk=bool(raw_attribute.get("fk", False)),
                nullable=bool(raw_attribute.get("nullable", True)),
                unique=bool(raw_attribute.get("unique", False)),
                default=raw_attribute.get("default"),
                note=raw_attribute.get("note"),
            )
            for raw_attribute in entity_data.get("attributes", []) or []
        ]
        entities.append(
            SchemaEntity(
                name=entity_data.get("name", ""),
                label=entity_data.get("label") or _entity_label(entity_data.get("name", "")),
                attributes=attributes,
                description=entity_data.get("description"),
            )
        )

    relationships: List[SchemaRelationship] = []
    for raw_relation in payload.get("relationships", []) or []:
        relation_data = raw_relation or {}
        relationships.append(
            SchemaRelationship(
                from_entity=relation_data.get("from_entity", ""),
                to_entity=relation_data.get("to_entity", ""),
                cardinality=relation_data.get("cardinality", "1:N"),
                label=relation_data.get("label", "relates_to"),
                reverse_label=relation_data.get("reverse_label"),
                bridge_entity=relation_data.get("bridge_entity"),
            )
        )

    return CurrentSchema(
        domain=payload.get("domain", "generic"),
        summary=payload.get("summary", ""),
        entities=entities,
        relationships=relationships,
        validation_notes=list(payload.get("validation_notes", []) or []),
        sample_data=payload.get("sample_data", {}) or {},
    )


def _mermaid_node_id(*parts: str) -> str:
    value = "_".join(part for part in (_snake_case(part) for part in parts) if part)
    value = re.sub(r"[^a-zA-Z0-9_]", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    if not value:
        value = "node"
    if value[0].isdigit():
        value = f"n_{value}"
    return value


class GeminiService:
    """Deterministic schema engine with the original Gemini service name."""

    def _detect_domain(self, text: str) -> str:
        scored = {}
        tokens = set(_tokenize(text))

        for domain, profile in DOMAIN_PROFILES.items():
            keywords = profile.get("keywords", set())
            if not keywords:
                continue
            score = len(tokens.intersection(keywords))
            scored[domain] = score

        if not scored:
            return "generic"

        best_domain, best_score = max(scored.items(), key=lambda item: item[1])
        if best_score == 0:
            return "generic"
        return best_domain

    def _extract_terms(self, text: str) -> List[str]:
        tokens = _tokenize(text)
        cleaned: List[str] = []

        for token in tokens:
            singular = _singularize(token.replace("_", ""))
            if singular in STOPWORDS or len(singular) < 3:
                continue
            cleaned.append(ENTITY_ALIASES.get(singular, singular))

        counts = Counter(cleaned)
        return [term for term, count in counts.items() if count > 1 or term in ENTITY_ALIASES.values()]

    def _candidate_custom_entities(self, text: str) -> List[str]:
        terms = self._extract_terms(text)
        return [term for term in terms if term not in ENTITY_TEMPLATES]

    def _is_weak_input(self, context: str) -> bool:
        tokens = [token for token in _tokenize(context) if token not in STOPWORDS]
        return len(tokens) < 5 and self._detect_domain(context) == "generic"

    def _build_entity_names(self, domain: str, context: str) -> List[str]:
        profile = DOMAIN_PROFILES.get(domain, DOMAIN_PROFILES["generic"])
        entity_names: "OrderedDict[str, None]" = OrderedDict()
        lowered_context = context.lower()
        weak_input = self._is_weak_input(context)

        for base_entity in profile.get("base_entities", []):
            entity_names[_snake_case(base_entity)] = None

        for trigger, entity_name in profile.get("optional_entities", {}).items():
            if trigger in lowered_context:
                entity_names[_snake_case(entity_name)] = None

        # Add any keywords that explicitly appear in the context.
        terms = set(self._extract_terms(context))
        for term in terms:
            canonical = ENTITY_ALIASES.get(term, term)
            if canonical in ENTITY_TEMPLATES or canonical in profile.get("optional_entities", {}).values():
                entity_names[_snake_case(canonical)] = None

        if domain == "generic" and not entity_names:
            for term in self._candidate_custom_entities(context)[:5]:
                entity_names[_snake_case(term)] = None

        if domain == "generic" and weak_input:
            entity_names["reference"] = None

        if domain == "generic" and len(entity_names) < 2:
            entity_names["actor"] = None
            entity_names["record"] = None

        return list(entity_names.keys())

    def _template_for_entity(self, entity_name: str) -> List[SchemaAttribute]:
        name = _snake_case(entity_name)
        if name in ENTITY_TEMPLATES:
            return _clone_attributes(ENTITY_TEMPLATES[name])

        # Generic fallback
        return [
            SchemaAttribute(name="id", type="int", pk=True, nullable=False),
            SchemaAttribute(name="name", type="string", nullable=False),
            SchemaAttribute(name="description", type="text"),
            SchemaAttribute(name="created_at", type="timestamp", default="CURRENT_TIMESTAMP"),
        ]

    def _apply_contextual_attributes(self, entity: SchemaEntity, context: str) -> None:
        text = context.lower()

        if any(word in text for word in ["email", "e-mail"]):
            if entity.name in {"customer", "account", "student", "instructor", "employee", "patient", "doctor"}:
                _append_if_missing(entity, SchemaAttribute(name="email", type="string", unique=True))

        if "phone" in text and entity.name in {"customer", "patient", "doctor", "employee"}:
            _append_if_missing(entity, SchemaAttribute(name="phone", type="string"))

        if "address" in text and entity.name in {"customer", "employee", "patient", "doctor", "supplier"}:
            _append_if_missing(entity, SchemaAttribute(name="address", type="string"))

        if "status" in text:
            _append_if_missing(entity, SchemaAttribute(name="status", type="string", default="'active'"))

        if any(word in text for word in ["date", "timestamp", "time", "scheduled"]):
            if entity.name in {"order", "appointment", "shipment", "visit", "prescription", "enrollment"}:
                _append_if_missing(entity, SchemaAttribute(name="created_at", type="timestamp", default="CURRENT_TIMESTAMP"))

        if entity.name == "product":
            if "sku" in text:
                _append_if_missing(entity, SchemaAttribute(name="sku", type="string", unique=True))
            if any(word in text for word in ["inventory", "stock"]):
                _append_if_missing(entity, SchemaAttribute(name="stock_quantity", type="int", default="0"))
            if "variant" in text:
                _append_if_missing(entity, SchemaAttribute(name="variant_name", type="string"))

        if entity.name == "order":
            if "total" in text:
                _append_if_missing(entity, SchemaAttribute(name="total_amount", type="decimal", nullable=False))
            if "number" in text:
                _append_if_missing(entity, SchemaAttribute(name="order_number", type="string", unique=True))

        if entity.name == "course" and "credit" in text:
            _append_if_missing(entity, SchemaAttribute(name="credits", type="int", default="3"))

        if entity.name == "patient" and "medical record" in text:
            _append_if_missing(entity, SchemaAttribute(name="medical_record_number", type="string", unique=True))

    def _build_relationship_specs(self, domain: str, entity_names: List[str]) -> List[SchemaRelationship]:
        profile_relationships = RELATIONSHIP_BLUEPRINTS.get(domain, RELATIONSHIP_BLUEPRINTS["generic"])
        entity_set = set(entity_names)
        relationships: List[SchemaRelationship] = []

        for from_entity, to_entity, cardinality, label, reverse_label in profile_relationships:
            if from_entity in entity_set and to_entity in entity_set:
                bridge_entity = None
                if cardinality == "M:N":
                    bridge_entity = BRIDGE_ENTITY_NAMES.get((from_entity, to_entity))
                    if not bridge_entity:
                        bridge_entity = f"{from_entity}_{to_entity}"
                relationships.append(
                    SchemaRelationship(
                        from_entity=from_entity,
                        to_entity=to_entity,
                        cardinality=cardinality,
                        label=label,
                        reverse_label=reverse_label,
                        bridge_entity=bridge_entity,
                    )
                )

        # Generic fallback if we still have nothing useful.
        if not relationships and len(entity_names) >= 2:
            relationships.append(
                SchemaRelationship(
                    from_entity=entity_names[0],
                    to_entity=entity_names[1],
                    cardinality="1:N",
                    label="relates_to",
                    reverse_label="belongs_to",
                )
            )

        return relationships

    def _validate_schema(self, schema: CurrentSchema, weak_input: bool = False) -> List[str]:
        notes: List[str] = []

        if not schema.entities:
            notes.append("No entities were detected, so a generic scaffold was used.")
            return notes

        for entity in schema.entities:
            has_primary_key = any(attribute.pk for attribute in entity.attributes)
            if not has_primary_key:
                notes.append(f"Entity `{entity.label or entity.name}` is missing a primary key.")

            if len(entity.attributes) < 2:
                notes.append(f"Entity `{entity.label or entity.name}` is very sparse and may need more attributes.")

        m2m_relationships = [relation for relation in schema.relationships if relation.cardinality == "M:N"]
        if m2m_relationships:
            bridge_names = {relation.bridge_entity for relation in m2m_relationships if relation.bridge_entity}
            for relation in m2m_relationships:
                if not relation.bridge_entity:
                    notes.append(f"Relationship `{relation.from_entity}` to `{relation.to_entity}` should be normalized through a bridge table.")
            if bridge_names:
                notes.append(f"Normalized {len(bridge_names)} many-to-many relationship(s) with bridge table(s): {', '.join(sorted(bridge_names))}.")
        else:
            notes.append("No many-to-many relationships detected.")

        if weak_input:
            notes.append("Input was weak, so the schema used a safer generic scaffold with inferred relationship roles.")

        if schema.domain == "generic":
            notes.append("Domain could not be resolved confidently; review the generated entities and rename them to your business terms.")

        return notes

    def _ensure_foreign_keys(
        self,
        entities: List[SchemaEntity],
        relationships: List[SchemaRelationship],
    ) -> Tuple[List[SchemaEntity], List[str]]:
        entity_map = {entity.name: entity for entity in entities}
        notes: List[str] = []

        for relation in relationships:
            parent = entity_map.get(relation.from_entity)
            child = entity_map.get(relation.to_entity)
            if not parent or not child:
                continue

            if relation.cardinality == "1:N":
                fk_name = f"{parent.name}_id"
                _append_if_missing(child, SchemaAttribute(name=fk_name, type="int", fk=True, nullable=False))
            elif relation.cardinality == "1:1":
                fk_name = f"{parent.name}_id"
                _append_if_missing(child, SchemaAttribute(name=fk_name, type="int", fk=True, nullable=False, unique=True))
            elif relation.cardinality == "M:N":
                bridge_name = relation.bridge_entity or f"{parent.name}_{child.name}"
                if bridge_name not in entity_map:
                    bridge_entity = SchemaEntity(
                        name=bridge_name,
                        label=_entity_label(bridge_name),
                        attributes=[],
                        description=f"Bridge entity for {parent.name} and {child.name}",
                    )
                    bridge_entity.attributes.append(SchemaAttribute(name=f"{parent.name}_id", type="int", fk=True, pk=True, nullable=False))
                    bridge_entity.attributes.append(SchemaAttribute(name=f"{child.name}_id", type="int", fk=True, pk=True, nullable=False))
                    for extra_attr in BRIDGE_EXTRA_ATTRIBUTES.get(bridge_name, []):
                        _append_if_missing(bridge_entity, extra_attr)
                    entities.append(bridge_entity)
                    entity_map[bridge_name] = bridge_entity
                    notes.append(f"Added bridge entity `{bridge_name}` to normalize the many-to-many relationship.")

        return entities, notes

    def _build_schema(self, nl_input: str, answers: Optional[str] = None, file_context: Optional[str] = None) -> CurrentSchema:
        answer_context = _extract_answer_context(answers)
        raw_context = "\n".join(part for part in [nl_input, answer_context, file_context or ""] if part)
        context = _normalise_text(raw_context)
        structured_dataset = self._parse_structured_dataset(raw_context)
        if structured_dataset:
            schema = CurrentSchema(
                domain=structured_dataset["domain"],
                summary=structured_dataset["summary"],
                entities=structured_dataset["entities"],
                relationships=structured_dataset["relationships"],
                validation_notes=list(structured_dataset["validation_notes"]),
                sample_data=structured_dataset["sample_data"],
            )
            validation_notes = self._validate_schema(schema, weak_input=False)
            schema.validation_notes.extend(validation_notes)
            if file_context:
                schema.validation_notes.append("File content was included in the schema hints.")
            return schema

        domain = self._detect_domain(context)
        weak_input = self._is_weak_input(context)
        entity_names = self._build_entity_names(domain, context)

        entities: List[SchemaEntity] = []
        for entity_name in entity_names:
            attrs = self._template_for_entity(entity_name)
            entity = SchemaEntity(
                name=_snake_case(entity_name),
                label=_entity_label(entity_name),
                attributes=attrs,
            )
            self._apply_contextual_attributes(entity, context)
            entities.append(entity)

        relationships = self._build_relationship_specs(domain, [entity.name for entity in entities])
        entities, notes = self._ensure_foreign_keys(entities, relationships)

        schema = CurrentSchema(
            domain=domain,
            summary="",
            entities=entities,
            relationships=relationships,
            validation_notes=[],
        )

        validation_notes = list(notes)
        validation_notes.extend(self._validate_schema(schema, weak_input=weak_input))
        if domain != "generic":
            validation_notes.append(f"Detected `{domain}` domain and applied a curated entity template.")
        if file_context:
            validation_notes.append("File content was included in the schema hints.")

        schema.summary = self._summarize_schema(domain, entities, relationships)
        schema.validation_notes = validation_notes
        return schema

    def _summarize_schema(self, domain: str, entities: List[SchemaEntity], relationships: List[SchemaRelationship]) -> str:
        entity_names = ", ".join(entity.label or _entity_label(entity.name) for entity in entities[:8])
        relation_count = len(relationships)
        return f"{_capitalize_words(domain)} schema with {len(entities)} entities, {relation_count} relationships, and normalized bridge tables where needed. Key entities: {entity_names}."

    def _looks_like_structured_dataset(self, context: str) -> bool:
        lowered = context.lower()
        markers = ("studentid:", "instructorid:", "courseid:", "enrollment:", "assignment:", "graderecord:", "department:")
        return any(marker in lowered for marker in markers)

    def _structured_questions(self) -> List[ClarifyingQuestion]:
        prompts = [
            ("natural keys", "Should the business IDs like StudentID, InstructorID, CourseID, and AssignmentID stay as the primary keys?", "keys", "Yes, keep the natural IDs as the primary keys."),
            ("department normalization", "Should Department be a separate lookup table shared by students, instructors, and courses?", "normalization", "Yes, normalize Department into its own table."),
            ("grade handling", "Should NA grades be stored as NULL in the database?", "data cleanup", "Yes, convert NA values to NULL."),
            ("grade history", "Should GradeRecord stay as a separate table for student-course-assignment marks?", "assessment", "Yes, keep it as a transactional table."),
        ]
        return [self._format_question(index + 1, prompt) for index, prompt in enumerate(prompts)]

    def _parse_structured_dataset(self, context: str) -> Optional[Dict[str, object]]:
        if not self._looks_like_structured_dataset(context):
            return None

        student_rows: List[Dict[str, object]] = []
        instructor_rows: List[Dict[str, object]] = []
        course_rows: List[Dict[str, object]] = []
        enrollment_rows: List[Dict[str, object]] = []
        assignment_rows: List[Dict[str, object]] = []
        grade_record_rows: List[Dict[str, object]] = []
        department_rows: "OrderedDict[str, Dict[str, object]]" = OrderedDict()
        observed_departments: List[str] = []
        notes: List[str] = ["Parsed structured academic records from the uploaded text."]

        def split_segments(raw_line: str) -> List[str]:
            return [segment.strip() for segment in raw_line.split("|") if segment.strip()]

        def parse_named_segments(segments: Sequence[str]) -> Dict[str, str]:
            parsed: Dict[str, str] = {}
            for segment in segments:
                if ":" not in segment:
                    continue
                key, value = segment.split(":", 1)
                parsed[key.strip().lower()] = value.strip()
            return parsed

        def normalise_text_value(value: Optional[str]) -> Optional[str]:
            if value is None:
                return None
            cleaned = value.strip()
            if not cleaned or cleaned.upper() in {"NA", "N/A", "NULL", "NONE", "-"}:
                return None
            return cleaned

        def normalise_numeric(value: Optional[str]) -> Optional[int]:
            text = normalise_text_value(value)
            if text is None:
                return None
            if re.fullmatch(r"-?\d+", text):
                return int(text)
            return None

        for raw_line in context.splitlines():
            line = raw_line.strip()
            lowered = line.lower()
            if not line:
                continue

            if lowered.startswith("studentid:"):
                prefix, *rest = split_segments(line)
                student_id = normalise_text_value(prefix.split(":", 1)[1]) if ":" in prefix else None
                fields = parse_named_segments(rest)
                if not student_id:
                    continue
                student_row = {
                    "student_id": student_id,
                    "full_name": normalise_text_value(fields.get("name")),
                    "age": normalise_numeric(fields.get("age")),
                    "gender": normalise_text_value(fields.get("gender")),
                    "department_name": normalise_text_value(fields.get("department")),
                    "year": normalise_numeric(fields.get("year")),
                }
                student_rows.append(student_row)
                if student_row["department_name"]:
                    observed_departments.append(str(student_row["department_name"]))
                continue

            if lowered.startswith("instructorid:"):
                prefix, *rest = split_segments(line)
                instructor_id = normalise_text_value(prefix.split(":", 1)[1]) if ":" in prefix else None
                fields = parse_named_segments(rest)
                if not instructor_id:
                    continue
                instructor_row = {
                    "instructor_id": instructor_id,
                    "full_name": normalise_text_value(fields.get("name")),
                    "age": normalise_numeric(fields.get("age")),
                    "department_name": normalise_text_value(fields.get("department")),
                    "email": normalise_text_value(fields.get("email")),
                }
                instructor_rows.append(instructor_row)
                if instructor_row["department_name"]:
                    observed_departments.append(str(instructor_row["department_name"]))
                continue

            if lowered.startswith("courseid:"):
                prefix, *rest = split_segments(line)
                course_id = normalise_text_value(prefix.split(":", 1)[1]) if ":" in prefix else None
                fields = parse_named_segments(rest)
                if not course_id:
                    continue
                course_row = {
                    "course_id": course_id,
                    "title": normalise_text_value(fields.get("title")),
                    "credits": normalise_numeric(fields.get("credits")),
                    "department_name": normalise_text_value(fields.get("department")),
                    "instructor_id": normalise_text_value(fields.get("instructor")),
                }
                course_rows.append(course_row)
                if course_row["department_name"]:
                    observed_departments.append(str(course_row["department_name"]))
                continue

            if lowered.startswith("enrollment:"):
                prefix, *rest = split_segments(line)
                enrollment_ref = normalise_text_value(prefix.split(":", 1)[1]) if ":" in prefix else None
                if not enrollment_ref:
                    continue
                match = re.match(r"^(.+?)\s*->\s*(.+)$", enrollment_ref)
                if not match:
                    continue
                fields = parse_named_segments(rest)
                enrollment_rows.append(
                    {
                        "student_id": normalise_text_value(match.group(1)),
                        "course_id": normalise_text_value(match.group(2)),
                        "status": normalise_text_value(fields.get("status")),
                        "grade": normalise_text_value(fields.get("grade")),
                        "enrolled_at": normalise_text_value(fields.get("enrolledat")),
                    }
                )
                continue

            if lowered.startswith("assignment:"):
                prefix, *rest = split_segments(line)
                assignment_id = normalise_text_value(prefix.split(":", 1)[1]) if ":" in prefix else None
                fields = parse_named_segments(rest)
                if not assignment_id:
                    continue
                assignment_rows.append(
                    {
                        "assignment_id": assignment_id,
                        "course_id": normalise_text_value(fields.get("course")),
                        "title": normalise_text_value(fields.get("title")),
                        "max_marks": normalise_numeric(fields.get("maxmarks")),
                    }
                )
                continue

            if lowered.startswith("graderecord:"):
                segments = split_segments(line)
                if len(segments) < 2:
                    continue
                prefix = segments[0]
                student_id = normalise_text_value(prefix.split(":", 1)[1]) if ":" in prefix else None
                course_id = normalise_text_value(segments[1])
                assignment_id = None
                if len(segments) > 2:
                    assignment_match = re.search(r"assignment\s+(.+)$", segments[2], re.IGNORECASE)
                    assignment_id = normalise_text_value(assignment_match.group(1) if assignment_match else segments[2])
                fields = parse_named_segments(segments[3:])
                grade_record_rows.append(
                    {
                        "student_id": student_id,
                        "course_id": course_id,
                        "assignment_id": assignment_id,
                        "marks": normalise_numeric(fields.get("marks")),
                    }
                )
                continue

            if lowered.startswith("department:"):
                prefix, *rest = split_segments(line)
                department_name = normalise_text_value(prefix.split(":", 1)[1]) if ":" in prefix else None
                fields = parse_named_segments(rest)
                if not department_name:
                    continue
                department_rows[department_name] = {
                    "department_name": department_name,
                    "hod_name": normalise_text_value(fields.get("hod")),
                }
                continue

        if not (student_rows or instructor_rows or course_rows or enrollment_rows or assignment_rows or grade_record_rows or department_rows):
            return None

        for dept_name in observed_departments:
            if dept_name and dept_name not in department_rows:
                department_rows[dept_name] = {"department_name": dept_name, "hod_name": None}

        entities = [
            SchemaEntity(
                name="department",
                label="DEPARTMENT",
                attributes=[
                    SchemaAttribute(name="department_name", type="string", pk=True, nullable=False, unique=True),
                    SchemaAttribute(name="hod_name", type="string"),
                ],
            ),
            SchemaEntity(
                name="student",
                label="STUDENT",
                attributes=[
                    SchemaAttribute(name="student_id", type="string", pk=True, nullable=False, unique=True),
                    SchemaAttribute(name="full_name", type="string", nullable=False),
                    SchemaAttribute(name="age", type="int"),
                    SchemaAttribute(name="gender", type="string"),
                    SchemaAttribute(name="department_name", type="string", fk=True),
                    SchemaAttribute(name="year", type="int"),
                ],
            ),
            SchemaEntity(
                name="instructor",
                label="INSTRUCTOR",
                attributes=[
                    SchemaAttribute(name="instructor_id", type="string", pk=True, nullable=False, unique=True),
                    SchemaAttribute(name="full_name", type="string", nullable=False),
                    SchemaAttribute(name="age", type="int"),
                    SchemaAttribute(name="department_name", type="string", fk=True),
                    SchemaAttribute(name="email", type="string", unique=True),
                ],
            ),
            SchemaEntity(
                name="course",
                label="COURSE",
                attributes=[
                    SchemaAttribute(name="course_id", type="string", pk=True, nullable=False, unique=True),
                    SchemaAttribute(name="title", type="string", nullable=False),
                    SchemaAttribute(name="credits", type="int"),
                    SchemaAttribute(name="department_name", type="string", fk=True),
                    SchemaAttribute(name="instructor_id", type="string", fk=True),
                ],
            ),
            SchemaEntity(
                name="enrollment",
                label="ENROLLMENT",
                attributes=[
                    SchemaAttribute(name="student_id", type="string", pk=True, fk=True, nullable=False),
                    SchemaAttribute(name="course_id", type="string", pk=True, fk=True, nullable=False),
                    SchemaAttribute(name="status", type="string"),
                    SchemaAttribute(name="grade", type="string"),
                    SchemaAttribute(name="enrolled_at", type="date"),
                ],
            ),
            SchemaEntity(
                name="assignment",
                label="ASSIGNMENT",
                attributes=[
                    SchemaAttribute(name="assignment_id", type="string", pk=True, nullable=False, unique=True),
                    SchemaAttribute(name="course_id", type="string", fk=True),
                    SchemaAttribute(name="title", type="string", nullable=False),
                    SchemaAttribute(name="max_marks", type="int"),
                ],
            ),
            SchemaEntity(
                name="grade_record",
                label="GRADE_RECORD",
                attributes=[
                    SchemaAttribute(name="student_id", type="string", pk=True, fk=True, nullable=False),
                    SchemaAttribute(name="course_id", type="string", pk=True, fk=True, nullable=False),
                    SchemaAttribute(name="assignment_id", type="string", pk=True, fk=True, nullable=False),
                    SchemaAttribute(name="marks", type="int"),
                ],
            ),
        ]

        relationships = [
            SchemaRelationship(from_entity="department", to_entity="student", cardinality="1:N", label="has_students", reverse_label="belongs_to"),
            SchemaRelationship(from_entity="department", to_entity="instructor", cardinality="1:N", label="has_instructors", reverse_label="belongs_to"),
            SchemaRelationship(from_entity="department", to_entity="course", cardinality="1:N", label="offers", reverse_label="belongs_to"),
            SchemaRelationship(from_entity="instructor", to_entity="course", cardinality="1:N", label="teaches", reverse_label="taught_by"),
            SchemaRelationship(from_entity="student", to_entity="enrollment", cardinality="1:N", label="registers", reverse_label="belongs_to"),
            SchemaRelationship(from_entity="course", to_entity="enrollment", cardinality="1:N", label="contains", reverse_label="belongs_to"),
            SchemaRelationship(from_entity="course", to_entity="assignment", cardinality="1:N", label="has_assignments", reverse_label="belongs_to"),
            SchemaRelationship(from_entity="student", to_entity="grade_record", cardinality="1:N", label="receives", reverse_label="belongs_to"),
            SchemaRelationship(from_entity="course", to_entity="grade_record", cardinality="1:N", label="produces", reverse_label="belongs_to"),
            SchemaRelationship(from_entity="assignment", to_entity="grade_record", cardinality="1:N", label="measures", reverse_label="belongs_to"),
        ]

        sample_data = {
            "department": list(department_rows.values()),
            "student": student_rows,
            "instructor": instructor_rows,
            "course": course_rows,
            "enrollment": enrollment_rows,
            "assignment": assignment_rows,
            "grade_record": grade_record_rows,
        }

        notes.append("Detected a structured academic dataset and mapped it to normalized entities.")
        notes.append("Natural IDs were preserved so the generated INSERT statements match the source rows.")

        summary = self._summarize_schema("education", entities, relationships)
        return {
            "domain": "education",
            "summary": summary,
            "entities": entities,
            "relationships": relationships,
            "validation_notes": notes,
            "sample_data": sample_data,
        }

    def _primary_key_columns(self, entity: SchemaEntity) -> List[str]:
        return [attribute.name for attribute in entity.attributes if attribute.pk]

    def _ordered_entities_for_sql(self, schema: CurrentSchema) -> List[SchemaEntity]:
        entity_map = {entity.name: entity for entity in schema.entities}
        entity_order = {entity.name: index for index, entity in enumerate(schema.entities)}
        dependencies: Dict[str, set[str]] = {}
        reverse_dependencies: Dict[str, set[str]] = {name: set() for name in entity_map}

        for entity in schema.entities:
            entity_deps: set[str] = set()
            for attribute in entity.attributes:
                if not attribute.fk:
                    continue
                target = self._guess_fk_target(entity.name, attribute.name)
                if target and target in entity_map and target != entity.name:
                    entity_deps.add(target)
            dependencies[entity.name] = entity_deps
            for dependency in entity_deps:
                reverse_dependencies.setdefault(dependency, set()).add(entity.name)

        queue = [entity.name for entity in schema.entities if not dependencies.get(entity.name)]
        ordered: List[str] = []
        seen: set[str] = set()

        while queue:
            current = queue.pop(0)
            if current in seen:
                continue
            seen.add(current)
            ordered.append(current)
            for dependent in sorted(reverse_dependencies.get(current, set()), key=lambda name: entity_order.get(name, 0)):
                dependencies[dependent].discard(current)
                if not dependencies[dependent] and dependent not in seen and dependent not in queue:
                    queue.append(dependent)

        if len(ordered) != len(entity_map):
            return list(schema.entities)
        return [entity_map[name] for name in ordered]

    def _sql_literal(self, value: Any, dialect: str) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        text = str(value).replace("'", "''")
        return f"'{text}'"

    def _insert_statements(self, schema: CurrentSchema, dialect: str) -> List[str]:
        statements: List[str] = []
        ordered_entities = self._ordered_entities_for_sql(schema)

        for entity in ordered_entities:
            rows = schema.sample_data.get(entity.name, [])
            if not rows:
                continue

            columns = [attribute.name for attribute in entity.attributes]
            value_groups: List[str] = []
            for row in rows:
                values = [self._sql_literal(row.get(column), dialect) for column in columns]
                value_groups.append(f"    ({', '.join(values)})")

            if not value_groups:
                continue

            statement = [
                f"INSERT INTO {_sql_table_name(entity.name)} ({', '.join(columns)}) VALUES",
                ",\n".join(value_groups) + ";",
            ]
            statements.append("\n".join(statement))

        return statements

    def _format_question(self, question_id: int, item: Tuple[str, str, str, str]) -> ClarifyingQuestion:
        focus, question, label, example = item
        return ClarifyingQuestion(
            id=f"q{question_id}",
            question=question,
            focus=label or focus,
            example_answer=example,
        )

    def _build_questions(self, nl_input: str, file_context: Optional[str] = None) -> List[ClarifyingQuestion]:
        raw_context = "\n".join(part for part in [nl_input, file_context or ""] if part)
        context = _normalise_text(raw_context)
        if self._looks_like_structured_dataset(raw_context):
            return self._structured_questions()
        domain = self._detect_domain(context)
        profile = DOMAIN_PROFILES.get(domain, DOMAIN_PROFILES["generic"])
        questions = [self._format_question(index + 1, question) for index, question in enumerate(profile["questions"])]

        if file_context:
            questions.append(
                ClarifyingQuestion(
                    id=f"q{len(questions) + 1}",
                    question="Should we preserve any field names from the uploaded document exactly, or normalize them into database-friendly names?",
                    focus="source mapping",
                    example_answer="Normalize names while keeping the source terminology in notes.",
                )
            )

        return questions[:5]

    def _resolve_sql_dialect(self, dialect: str) -> str:
        key = _snake_case(dialect).replace("_", "")
        if key in {"postgres", "postgresql"}:
            return "postgresql"
        if key == "mysql":
            return "mysql"
        if key in {"sqlserver", "mssql"}:
            return "sqlserver"
        if key == "oracle":
            return "oracle"
        if key == "sqlite":
            return "sqlite"
        return "postgresql"

    def _sql_type(self, column: SchemaAttribute, dialect: str) -> str:
        dialect_map = SQL_TYPE_MAP[dialect]
        if column.pk and column.name == "id":
            return dialect_map["id"]
        if column.type == "int" and column.pk and dialect == "sqlite":
            return "INTEGER"
        return dialect_map.get(column.type, dialect_map.get("string", "VARCHAR(255)"))

    def _column_sql(self, column: SchemaAttribute, dialect: str) -> str:
        col_type = self._sql_type(column, dialect)
        pieces = [column.name, col_type]

        if dialect != "sqlite" and column.pk and column.name == "id":
            if dialect == "postgresql":
                pieces = [column.name, "SERIAL", "PRIMARY KEY"]
                return " ".join(pieces)
            if dialect == "mysql":
                pieces = [column.name, "INT AUTO_INCREMENT", "PRIMARY KEY"]
                return " ".join(pieces)
            if dialect == "sqlserver":
                pieces = [column.name, "INT IDENTITY(1,1)", "PRIMARY KEY"]
                return " ".join(pieces)
            if dialect == "oracle":
                pieces = [column.name, "NUMBER GENERATED BY DEFAULT AS IDENTITY", "PRIMARY KEY"]
                return " ".join(pieces)

        if column.pk:
            pieces.append("PRIMARY KEY")
        if not column.nullable and not column.pk and dialect != "sqlite":
            pieces.append("NOT NULL")
        if column.unique:
            pieces.append("UNIQUE")
        if column.default is not None:
            pieces.append(f"DEFAULT {column.default}")
        if column.fk and dialect != "sqlite":
            pieces.append("REFERENCES")
        return " ".join(pieces)

    def _render_mermaid(self, schema: CurrentSchema) -> str:
        schema_comment = json.dumps(_schema_payload(schema), ensure_ascii=False, separators=(",", ":"))
        lines = [
            f"%% schemaflow:{schema_comment}",
            "flowchart TB",
            "%% Chen-style ER diagram generated by SchemaFlow",
        ]

        rendered_entities: set[str] = set()
        rendered_attribute_nodes: set[str] = set()
        rendered_relationships: set[Tuple[str, str, str]] = set()

        def add_entity(entity: SchemaEntity) -> None:
            entity_id = _mermaid_node_id("entity", entity.name)
            if entity_id in rendered_entities:
                return
            rendered_entities.add(entity_id)
            label = (entity.label or _entity_label(entity.name)).replace('"', "'")
            lines.append(f'    {entity_id}["{label}"]')

            for attribute in entity.attributes:
                attr_id = _mermaid_node_id("attr", entity.name, attribute.name)
                if attr_id in rendered_attribute_nodes:
                    continue
                rendered_attribute_nodes.add(attr_id)
                attr_label = attribute.name.replace('"', "'")
                if attribute.pk and attribute.fk:
                    attr_label = f"{attr_label} (PK, FK)"
                elif attribute.pk:
                    attr_label = f"{attr_label} (PK)"
                elif attribute.fk:
                    attr_label = f"{attr_label} (FK)"
                elif attribute.unique:
                    attr_label = f"{attr_label} (UK)"
                lines.append(f'    {attr_id}(["{attr_label}"])')
                lines.append(f"    {entity_id} --- {attr_id}")

        def add_relationship(relation: SchemaRelationship) -> None:
            rel_id = _mermaid_node_id("rel", relation.from_entity, relation.label, relation.to_entity)
            key = (relation.from_entity, relation.to_entity, relation.label)
            if key in rendered_relationships:
                return
            rendered_relationships.add(key)

            rel_label = (relation.label or "relates_to").replace('"', "'")
            lines.append(f'    {rel_id}{{"{rel_label}"}}')

            if relation.cardinality == "1:1":
                left_cardinality, right_cardinality = "1", "1"
            elif relation.cardinality == "M:N":
                left_cardinality, right_cardinality = "N", "N"
            else:
                left_cardinality, right_cardinality = "1", "N"

            source_id = _mermaid_node_id("entity", relation.from_entity)
            target_id = _mermaid_node_id("entity", relation.to_entity)
            lines.append(f"    {source_id} ---|{left_cardinality}| {rel_id}")
            lines.append(f"    {rel_id} ---|{right_cardinality}| {target_id}")

            if relation.cardinality == "M:N" and relation.bridge_entity:
                bridge_id = _mermaid_node_id("entity", relation.bridge_entity)
                lines.append(f"    {bridge_id} -.-> {rel_id}")

        for entity in schema.entities:
            add_entity(entity)

        for relation in schema.relationships:
            add_relationship(relation)

        return "\n".join(lines)

    def _render_sql(self, schema: CurrentSchema, dialect: str) -> Tuple[str, List[str]]:
        resolved_dialect = self._resolve_sql_dialect(dialect)
        entity_map = {entity.name: entity for entity in schema.entities}
        statements: List[str] = []
        validation_notes = list(schema.validation_notes)

        ordered_entities = self._ordered_entities_for_sql(schema)

        for entity in ordered_entities:
            table_name = _sql_table_name(entity.name)
            column_defs: List[str] = []
            foreign_keys: List[str] = []
            unique_constraints: List[str] = []
            pk_columns: List[str] = []

            for column in entity.attributes:
                col_type = self._sql_type(column, resolved_dialect)
                if column.pk and column.name == "id" and resolved_dialect != "sqlite":
                    if resolved_dialect == "postgresql":
                        column_defs.append("id SERIAL PRIMARY KEY")
                    elif resolved_dialect == "mysql":
                        column_defs.append("id INT AUTO_INCREMENT PRIMARY KEY")
                    elif resolved_dialect == "sqlserver":
                        column_defs.append("id INT IDENTITY(1,1) PRIMARY KEY")
                    elif resolved_dialect == "oracle":
                        column_defs.append("id NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY")
                    continue
                if column.pk and column.name == "id" and resolved_dialect == "sqlite":
                    column_defs.append("id INTEGER PRIMARY KEY AUTOINCREMENT")
                    continue

                if column.pk:
                    pk_columns.append(column.name)
                column_sql = f"{column.name} {col_type}"
                if not column.nullable and resolved_dialect != "sqlite":
                    column_sql += " NOT NULL"
                if column.unique:
                    column_sql += " UNIQUE"
                if column.default is not None:
                    column_sql += f" DEFAULT {column.default}"
                column_defs.append(column_sql)

                if column.fk:
                    referenced_table = self._guess_fk_target(entity.name, column.name)
                    if referenced_table and referenced_table in entity_map:
                        referenced_entity = entity_map[referenced_table]
                        referenced_columns = self._primary_key_columns(referenced_entity)
                        if len(referenced_columns) == 1:
                            foreign_keys.append(
                                f"FOREIGN KEY ({column.name}) REFERENCES {_sql_table_name(referenced_table)}({referenced_columns[0]})"
                            )
                        else:
                            validation_notes.append(
                                f"Skipped foreign key reference for `{entity.name}.{column.name}` because `{referenced_table}` uses a composite primary key."
                            )

            if pk_columns and not any("PRIMARY KEY" in item for item in column_defs):
                column_defs.append(f"PRIMARY KEY ({', '.join(pk_columns)})")

            ddl_lines = [f"CREATE TABLE {table_name} ("]
            ddl_lines.extend(f"    {definition}," for definition in column_defs + foreign_keys)
            if ddl_lines[-1].endswith(","):
                ddl_lines[-1] = ddl_lines[-1][:-1]
            ddl_lines.append(");")
            statements.append("\n".join(ddl_lines))

            for column in entity.attributes:
                if column.unique and column.name not in {"id"}:
                    unique_constraints.append(column.name)
            if unique_constraints:
                validation_notes.append(
                    f"Table `{_sql_table_name(entity.name)}` has unique constraints on {', '.join(unique_constraints)}."
                )

        insert_statements = self._insert_statements(schema, resolved_dialect)
        if insert_statements:
            statements.append("-- Seed data extracted from the uploaded text")
            statements.extend(insert_statements)

        return "\n\n".join(statements), validation_notes

    def _guess_fk_target(self, entity_name: str, column_name: str) -> Optional[str]:
        if column_name == "id":
            return None

        prefix = column_name.removesuffix("_id")
        if prefix:
            return _snake_case(prefix)

        if entity_name in {"order_item", "cart_item"}:
            if column_name == "order_id":
                return "order"
            if column_name == "product_id":
                return "product"
            if column_name == "cart_id":
                return "cart"

        if entity_name == "enrollment":
            if column_name == "student_id":
                return "student"
            if column_name == "course_id":
                return "course"

        if entity_name == "project_member":
            if column_name == "project_id":
                return "project"
            if column_name == "employee_id":
                return "employee"

        return None

    def _parse_schema_from_mermaid(self, mermaid_diagram: str) -> CurrentSchema:
        for raw_line in mermaid_diagram.splitlines():
            line = raw_line.strip()
            if not line.startswith("%% schemaflow:"):
                continue
            payload_text = line.split("%% schemaflow:", 1)[1].strip()
            if not payload_text:
                continue
            try:
                payload = json.loads(payload_text)
            except json.JSONDecodeError:
                logger.warning("Unable to decode embedded schema payload from Mermaid comment.")
                break
            return _schema_from_payload(payload)

        entities: List[SchemaEntity] = []
        relationships: List[SchemaRelationship] = []

        entity_block_pattern = re.compile(r"^\s*([A-Z0-9_]+)\s*\{\s*\n([\s\S]*?)^\s*\}\s*$", re.MULTILINE)

        for match in entity_block_pattern.finditer(mermaid_diagram):
            entity_name = _snake_case(match.group(1))
            block_text = match.group(2)
            attributes: List[SchemaAttribute] = []

            for raw_line in block_text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) < 2:
                    continue
                type_name = parts[0]
                column_name = parts[1]
                flags = {part.upper() for part in parts[2:]}
                attributes.append(
                    SchemaAttribute(
                        name=column_name,
                        type=TYPE_ALIASES.get(type_name.lower(), type_name.lower()),
                        pk="PK" in flags,
                        fk="FK" in flags,
                        unique="UK" in flags,
                        nullable="PK" not in flags,
                    )
                )

            entities.append(
                SchemaEntity(
                    name=entity_name,
                    label=_entity_label(entity_name),
                    attributes=attributes,
                )
            )

        relationship_pattern = re.compile(
            r"^\s*([A-Z0-9_]+)\s+(\|\|--\|\||\|\|--o\{|\}o--o\{|\}\|--\|\{)\s+([A-Z0-9_]+)\s*:\s*(.+?)\s*$",
            re.MULTILINE,
        )
        for match in relationship_pattern.finditer(mermaid_diagram):
            source = _snake_case(match.group(1))
            connector = match.group(2)
            target = _snake_case(match.group(3))
            label = match.group(4).strip()
            cardinality = "1:1" if connector == "||--||" else "M:N" if connector == "}o--o{" else "1:N"
            relationships.append(
                SchemaRelationship(
                    from_entity=source,
                    to_entity=target,
                    cardinality=cardinality,
                    label=label,
                )
            )

        domain = self._detect_domain(mermaid_diagram)
        summary = self._summarize_schema(domain, entities, relationships)
        return CurrentSchema(
            domain=domain,
            summary=summary,
            entities=entities,
            relationships=relationships,
            validation_notes=[],
        )

    async def generate_questions(self, nl_input: str, file_context: Optional[str] = None) -> List[ClarifyingQuestion]:
        logger.info("Generating clarifying questions")
        return self._build_questions(nl_input, file_context)

    async def generate_mermaid(
        self,
        nl_input: str,
        questions_answers: str,
        existing_schema: Optional[str] = None,
        file_context: Optional[str] = None,
    ) -> Tuple[str, CurrentSchema, List[str]]:
        logger.info("Generating Chen Mermaid diagram")
        schema = self._build_schema(nl_input, answers=questions_answers, file_context=file_context)

        if existing_schema:
            # If a prior diagram exists, preserve its entities where possible and
            # let the current answers refine the new schema.
            previous_schema = self._parse_schema_from_mermaid(existing_schema)
            if previous_schema.entities:
                previous_entity_names = {entity.name for entity in previous_schema.entities}
                merged_entities = {entity.name: entity for entity in schema.entities}
                for entity in previous_schema.entities:
                    merged_entities.setdefault(entity.name, entity)
                schema.entities = list(merged_entities.values())
                merged_sample_data = dict(previous_schema.sample_data)
                merged_sample_data.update(schema.sample_data)
                schema.sample_data = merged_sample_data
                schema.validation_notes.append(
                    f"Preserved {len(previous_entity_names)} entity definitions from the previous schema."
                )

        mermaid = self._render_mermaid(schema)
        return mermaid, schema, schema.validation_notes

    async def generate_sql(self, mermaid_diagram: str, dialect: str = "PostgreSQL") -> Tuple[str, List[str]]:
        logger.info("Generating SQL for dialect: %s", dialect)
        schema = self._parse_schema_from_mermaid(mermaid_diagram)
        sql, notes = self._render_sql(schema, dialect)
        return sql, notes

    async def refine_schema(self, current_mermaid: str, user_request: str) -> Tuple[str, CurrentSchema, List[str]]:
        logger.info("Refining schema based on user request")
        schema = self._parse_schema_from_mermaid(current_mermaid)
        request_text = user_request.lower()

        if "timestamp" in request_text or "audit" in request_text:
            for entity in schema.entities:
                if entity.name not in {"order_item", "enrollment", "cart_item", "project_member"}:
                    _append_if_missing(entity, SchemaAttribute(name="updated_at", type="timestamp", default="CURRENT_TIMESTAMP"))
                    _append_if_missing(entity, SchemaAttribute(name="created_at", type="timestamp", default="CURRENT_TIMESTAMP"))

        rename_match = re.search(r"rename\s+([a-zA-Z_ ]+?)\s+to\s+([a-zA-Z_ ]+)", request_text)
        if rename_match:
            old_name = _snake_case(rename_match.group(1))
            new_name = _snake_case(rename_match.group(2))
            for entity in schema.entities:
                if entity.name == old_name:
                    entity.name = new_name
                    entity.label = _entity_label(new_name)
            for relation in schema.relationships:
                if relation.from_entity == old_name:
                    relation.from_entity = new_name
                if relation.to_entity == old_name:
                    relation.to_entity = new_name

        if "many to many" in request_text or "many-to-many" in request_text:
            entity_names = [entity.name for entity in schema.entities]
            if len(entity_names) >= 2:
                source, target = entity_names[0], entity_names[1]
                bridge_name = BRIDGE_ENTITY_NAMES.get((source, target), f"{source}_{target}")
                relationship = SchemaRelationship(
                    from_entity=source,
                    to_entity=target,
                    cardinality="M:N",
                    label="relates_to",
                    reverse_label="related_to",
                    bridge_entity=bridge_name,
                )
                schema.relationships.append(relationship)
                schema.entities, notes = self._ensure_foreign_keys(schema.entities, [relationship])
                schema.validation_notes.extend(notes)

        schema.summary = self._summarize_schema(schema.domain, schema.entities, schema.relationships)
        mermaid = self._render_mermaid(schema)
        schema.validation_notes.append("Applied user-requested refinement heuristics.")
        return mermaid, schema, schema.validation_notes


gemini_service = GeminiService()
