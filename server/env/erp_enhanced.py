"""
Enhanced ERP System for ESIG — realistic enterprise resource planning.

Includes:
  - Orders with full lifecycle (draft → shipped → delivered → paid)
  - Inventory tracking with prerequisites
  - Shipping/tracking system with statuses
  - Payment lifecycle with multiple methods
  - Multi-vendor scenarios with dependencies
  - Financial reconciliation
"""
from __future__ import annotations
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import random


class OrderStatus(str, Enum):
    """Order lifecycle states."""
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    """Payment lifecycle states."""
    UNPAID = "unpaid"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    DISPUTED = "disputed"


class ShippingStatus(str, Enum):
    """Shipping lifecycle states."""
    PENDING = "pending"
    PICKED = "picked"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    EXCEPTION = "exception"


@dataclass
class InventoryItem:
    """Inventory stock unit."""
    sku: str
    product_name: str
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int
    warehouse_location: str
    last_stock_check: str
    reorder_point: int
    supplier_id: str


@dataclass
class ShippingDetail:
    """Shipping and tracking information."""
    tracking_number: str
    carrier: str
    status: ShippingStatus
    shipped_date: str
    estimated_delivery: str
    actual_delivery: Optional[str]
    shipping_address: str
    carrier_contact: str


@dataclass
class PaymentDetail:
    """Payment information and history."""
    payment_method: str  # "credit_card", "bank_transfer", "check", "net_30"
    status: PaymentStatus
    amount_paid: float
    amount_due: float
    due_date: str
    paid_date: Optional[str]
    payment_reference: str
    currency: str


@dataclass
class OrderLineItem:
    """Single line in an order."""
    line_number: int
    sku: str
    product_name: str
    quantity: int
    unit_price: float
    total_price: float
    discount_percent: float
    tax_amount: float
    vendor_id: str


@dataclass
class Order:
    """Enhanced order model with full lifecycle."""
    order_id: str
    customer_id: str
    order_date: str
    status: OrderStatus
    line_items: List[OrderLineItem]
    shipping_detail: ShippingDetail
    payment_detail: PaymentDetail
    total_amount: float
    subtotal: float
    tax_total: float
    shipping_cost: float
    discount_total: float
    notes: str
    po_reference: Optional[str]


class EnhancedERPDatabase:
    """Enhanced ERP database with realistic scenarios."""

    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.inventory: Dict[str, InventoryItem] = {}
        self.vendors: Dict[str, Dict[str, Any]] = {}
        self.seed_database()

    def seed_database(self) -> None:
        """Populate with realistic test data."""
        # Clear existing
        self.orders = {}
        self.inventory = {}
        self.vendors = {}

        # Add vendors
        self.vendors = {
            "VENDOR-001": {
                "name": "Widget Manufacturing Co",
                "contact": "vendor@widgets.com",
                "payment_terms": "net_30",
                "status": "active",
            },
            "VENDOR-002": {
                "name": "Software Solutions Ltd",
                "contact": "sales@softsol.com",
                "payment_terms": "net_60",
                "status": "active",
            },
            "VENDOR-003": {
                "name": "Enterprise Services Group",
                "contact": "support@esg.com",
                "payment_terms": "net_45",
                "status": "active",
            },
        }

        # Add inventory
        inventory_data = [
            ("SKU-001", "Widget Pro", 150, 30, "WH-001", "VENDOR-001"),
            ("SKU-002", "Enterprise License", 999, 5, "WH-002", "VENDOR-002"),
            ("SKU-003", "Support Package", 50, 10, "WH-001", "VENDOR-003"),
            ("SKU-004", "Premium Bundle", 25, 8, "WH-002", "VENDOR-001"),
            ("SKU-005", "Basic Plan", 200, 20, "WH-001", "VENDOR-002"),
        ]

        for sku, name, qty, reserved, loc, vendor in inventory_data:
            self.inventory[sku] = InventoryItem(
                sku=sku,
                product_name=name,
                quantity_on_hand=qty,
                quantity_reserved=reserved,
                quantity_available=qty - reserved,
                warehouse_location=loc,
                last_stock_check=datetime.now().isoformat(),
                reorder_point=20,
                supplier_id=vendor,
            )

        # Add orders with various states
        self._create_sample_orders()

    def _create_sample_orders(self) -> None:
        """Create orders in different lifecycle states."""
        now = datetime.now()

        # Order 1: Delivered, paid (COMPLETED)
        order1 = Order(
            order_id="ORD-2024-001",
            customer_id="CUST001",
            order_date=(now - timedelta(days=30)).isoformat(),
            status=OrderStatus.DELIVERED,
            line_items=[
                OrderLineItem(
                    line_number=1,
                    sku="SKU-001",
                    product_name="Widget Pro",
                    quantity=10,
                    unit_price=100.0,
                    total_price=1000.0,
                    discount_percent=0.0,
                    tax_amount=100.0,
                    vendor_id="VENDOR-001",
                )
            ],
            shipping_detail=ShippingDetail(
                tracking_number="TRACK-001",
                carrier="FedEx",
                status=ShippingStatus.DELIVERED,
                shipped_date=(now - timedelta(days=25)).isoformat(),
                estimated_delivery=(now - timedelta(days=20)).isoformat(),
                actual_delivery=(now - timedelta(days=20)).isoformat(),
                shipping_address="123 Main St, City, State 12345",
                carrier_contact="1-800-FEDEX",
            ),
            payment_detail=PaymentDetail(
                payment_method="bank_transfer",
                status=PaymentStatus.PAID,
                amount_paid=1100.0,
                amount_due=0.0,
                due_date=(now - timedelta(days=30)).isoformat(),
                paid_date=(now - timedelta(days=20)).isoformat(),
                payment_reference="WIRE-2024-0001",
                currency="USD",
            ),
            total_amount=1100.0,
            subtotal=1000.0,
            tax_total=100.0,
            shipping_cost=0.0,
            discount_total=0.0,
            notes="Delivered successfully",
            po_reference="PO-2024-0001",
        )
        self.orders["ORD-2024-001"] = order1

        # Order 2: In transit, unpaid (realistic scenario)
        order2 = Order(
            order_id="ORD-2024-002",
            customer_id="CUST002",
            order_date=(now - timedelta(days=7)).isoformat(),
            status=OrderStatus.IN_TRANSIT,
            line_items=[
                OrderLineItem(
                    line_number=1,
                    sku="SKU-002",
                    product_name="Enterprise License",
                    quantity=1,
                    unit_price=5000.0,
                    total_price=5000.0,
                    discount_percent=0.1,
                    tax_amount=450.0,
                    vendor_id="VENDOR-002",
                )
            ],
            shipping_detail=ShippingDetail(
                tracking_number="TRACK-002",
                carrier="UPS",
                status=ShippingStatus.IN_TRANSIT,
                shipped_date=(now - timedelta(days=3)).isoformat(),
                estimated_delivery=(now + timedelta(days=2)).isoformat(),
                actual_delivery=None,
                shipping_address="456 Business Ave, City, State 67890",
                carrier_contact="1-800-UPS",
            ),
            payment_detail=PaymentDetail(
                payment_method="net_60",
                status=PaymentStatus.UNPAID,
                amount_paid=0.0,
                amount_due=4950.0,
                due_date=(now + timedelta(days=30)).isoformat(),
                paid_date=None,
                payment_reference="INV-2024-0001",
                currency="USD",
            ),
            total_amount=4950.0,
            subtotal=4500.0,
            tax_total=450.0,
            shipping_cost=0.0,
            discount_total=500.0,
            notes="",
            po_reference="PO-2024-0002",
        )
        self.orders["ORD-2024-002"] = order2

        # Order 3: Processing, partially paid
        order3 = Order(
            order_id="ORD-2024-003",
            customer_id="CUST001",
            order_date=(now - timedelta(days=5)).isoformat(),
            status=OrderStatus.PROCESSING,
            line_items=[
                OrderLineItem(
                    line_number=1,
                    sku="SKU-003",
                    product_name="Support Package",
                    quantity=3,
                    unit_price=500.0,
                    total_price=1500.0,
                    discount_percent=0.0,
                    tax_amount=150.0,
                    vendor_id="VENDOR-003",
                ),
                OrderLineItem(
                    line_number=2,
                    sku="SKU-001",
                    product_name="Widget Pro",
                    quantity=5,
                    unit_price=100.0,
                    total_price=500.0,
                    discount_percent=0.05,
                    tax_amount=45.0,
                    vendor_id="VENDOR-001",
                ),
            ],
            shipping_detail=ShippingDetail(
                tracking_number="TRACK-003",
                carrier="DHL",
                status=ShippingStatus.PENDING,
                shipped_date="",
                estimated_delivery=(now + timedelta(days=7)).isoformat(),
                actual_delivery=None,
                shipping_address="789 Enterprise Blvd, City, State 11111",
                carrier_contact="1-800-DHL",
            ),
            payment_detail=PaymentDetail(
                payment_method="credit_card",
                status=PaymentStatus.PARTIALLY_PAID,
                amount_paid=1000.0,
                amount_due=795.0,
                due_date=(now + timedelta(days=15)).isoformat(),
                paid_date=(now - timedelta(days=2)).isoformat(),
                payment_reference="CC-2024-0001",
                currency="USD",
            ),
            total_amount=1795.0,
            subtotal=2000.0,
            tax_total=195.0,
            shipping_cost=0.0,
            discount_total=50.0,
            notes="Awaiting inventory confirmation for SKU-003",
            po_reference="PO-2024-0003",
        )
        self.orders["ORD-2024-003"] = order3

    def query_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self.orders.get(order_id)

    def query_orders_by_customer(self, customer_id: str) -> List[Order]:
        """Get all orders for a customer."""
        return [o for o in self.orders.values() if o.customer_id == customer_id]

    def query_inventory(self, sku: str) -> Optional[InventoryItem]:
        """Get inventory info for SKU."""
        return self.inventory.get(sku)

    def query_vendor(self, vendor_id: str) -> Optional[Dict[str, Any]]:
        """Get vendor information."""
        return self.vendors.get(vendor_id)

    def check_inventory_availability(self, sku: str, quantity: int) -> bool:
        """Check if SKU has sufficient availability."""
        item = self.inventory.get(sku)
        if not item:
            return False
        return item.quantity_available >= quantity

    def get_order_summary(self, order_id: str) -> Dict[str, Any]:
        """Get comprehensive order summary for agent."""
        order = self.query_order(order_id)
        if not order:
            return {"error": f"Order {order_id} not found"}

        return {
            "order_id": order.order_id,
            "customer_id": order.customer_id,
            "order_date": order.order_date,
            "status": order.status.value,
            "line_items": [asdict(li) for li in order.line_items],
            "shipping": asdict(order.shipping_detail),
            "payment": {
                "method": order.payment_detail.payment_method,
                "status": order.payment_detail.status.value,
                "amount_paid": order.payment_detail.amount_paid,
                "amount_due": order.payment_detail.amount_due,
                "due_date": order.payment_detail.due_date,
            },
            "totals": {
                "subtotal": order.subtotal,
                "tax": order.tax_total,
                "shipping": order.shipping_cost,
                "discount": order.discount_total,
                "total": order.total_amount,
            },
            "notes": order.notes,
            "po_reference": order.po_reference,
        }

    def record_payment(
        self, order_id: str, amount: float, payment_reference: str
    ) -> bool:
        """Record a payment against an order."""
        order = self.query_order(order_id)
        if not order:
            return False

        order.payment_detail.amount_paid += amount
        new_due = order.total_amount - order.payment_detail.amount_paid

        if new_due <= 0:
            order.payment_detail.status = PaymentStatus.PAID
            order.payment_detail.amount_due = 0.0
        else:
            order.payment_detail.status = PaymentStatus.PARTIALLY_PAID
            order.payment_detail.amount_due = new_due

        order.payment_detail.payment_reference = payment_reference
        return True

    def update_shipping_status(self, order_id: str, status: ShippingStatus) -> bool:
        """Update shipping status."""
        order = self.query_order(order_id)
        if not order:
            return False

        order.shipping_detail.status = status

        if status == ShippingStatus.DELIVERED:
            order.shipping_detail.actual_delivery = datetime.now().isoformat()
            order.status = OrderStatus.DELIVERED

        return True


# Global instance
_erp_db = None


def get_erp_database() -> EnhancedERPDatabase:
    """Get or create global ERP database."""
    global _erp_db
    if _erp_db is None:
        _erp_db = EnhancedERPDatabase()
    return _erp_db
