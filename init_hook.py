import logging

from odoo.tools.sql import column_exists

logger = logging.getLogger(__name__)


def pre_init_hook(cr):
    """
    The objective of this hook is to speed up the installation
    of the module on an existing Odoo instance.
    """
    store_exception_fields(cr)


def store_exception_fields(cr):
    if not column_exists(cr, "sale_order_line", "qty_available"):
        logger.info("Creating field qty_available on sale_order_line")
        cr.execute(
            """
            ALTER TABLE sale_order_line
            ADD COLUMN qty_available float DEFAULT 0;
            COMMENT ON COLUMN sale_order_line.qty_available IS 'qty_available';
            """
        )
    if not column_exists(cr, "sale_order_line", "margin_disp"):
        logger.info("Creating field margin_disp on sale_order_line")
        cr.execute(
            """
            ALTER TABLE sale_order_line
            ADD COLUMN margin_disp float DEFAULT 0;
            COMMENT ON COLUMN sale_order_line.margin_disp IS 'margin_disp';
            """
        )
    if not column_exists(cr, "sale_order_line", "price_tax_disp"):
        logger.info("Creating field price_tax_disp on sale_order_line")
        cr.execute(
            """
            ALTER TABLE sale_order_line
            ADD COLUMN price_tax_disp float DEFAULT 0;
            COMMENT ON COLUMN sale_order_line.price_tax_disp IS 'price_tax_disp';
            """
        )
    if not column_exists(cr, "sale_order_line", "price_total_disp"):
        logger.info("Creating field price_total_disp on sale_order_line")
        cr.execute(
            """
            ALTER TABLE sale_order_line
            ADD COLUMN price_total_disp float DEFAULT 0;
            COMMENT ON COLUMN sale_order_line.price_total_disp IS 'price_total_disp';
            """
        )
    if not column_exists(cr, "sale_order_line", "price_subtotal_disp"):
        logger.info("Creating field price_subtotal_disp on sale_order_line")
        cr.execute(
            """
            ALTER TABLE sale_order_line
            ADD COLUMN price_subtotal_disp float DEFAULT 0;
            COMMENT ON COLUMN sale_order_line.price_subtotal_disp IS 'price_subtotal_disp';
            """
        )
    if not column_exists(cr, "sale_order", "margin_disp"):
        logger.info("Creating field margin_disp on sale_order")
        cr.execute(
            """
            ALTER TABLE sale_order
            ADD COLUMN margin_disp float DEFAULT 0;
            COMMENT ON COLUMN sale_order.margin_disp IS 'margin_disp';
            """
        )
    if not column_exists(cr, "sale_order", "margin_porciento"):
        logger.info("Creating field margin_porciento on sale_order")
        cr.execute(
            """
            ALTER TABLE sale_order
            ADD COLUMN margin_porciento float DEFAULT 0;
            COMMENT ON COLUMN sale_order.margin_porciento IS 'margin_porciento';
            """
        )
    if not column_exists(cr, "sale_order", "margin_porciento_disp"):
        logger.info("Creating field margin_porciento_disp on sale_order")
        cr.execute(
            """
            ALTER TABLE sale_order
            ADD COLUMN margin_porciento_disp float DEFAULT 0;
            COMMENT ON COLUMN sale_order.margin_porciento_disp IS 'margin_porciento_disp';
            """
        )
    if not column_exists(cr, "sale_order", "amount_untaxed_disp"):
        logger.info("Creating field amount_untaxed_disp on sale_order")
        cr.execute(
            """
            ALTER TABLE sale_order
            ADD COLUMN amount_untaxed_disp float DEFAULT 0;
            COMMENT ON COLUMN sale_order.amount_untaxed_disp IS 'amount_untaxed_disp';
            """
        )
    if not column_exists(cr, "sale_order", "amount_tax_disp"):
        logger.info("Creating field amount_tax_disp on sale_order")
        cr.execute(
            """
            ALTER TABLE sale_order
            ADD COLUMN amount_tax_disp float DEFAULT 0;
            COMMENT ON COLUMN sale_order.amount_tax_disp IS 'amount_tax_disp';
            """
        )
    if not column_exists(cr, "sale_order", "amount_total_disp"):
        logger.info("Creating field amount_total_disp on sale_order")
        cr.execute(
            """
            ALTER TABLE sale_order
            ADD COLUMN amount_total_disp float DEFAULT 0;
            COMMENT ON COLUMN sale_order.amount_total_disp IS 'amount_total_disp';
            """
        )
