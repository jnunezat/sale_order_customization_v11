from odoo import api, fields, models, exceptions
from odoo.addons import decimal_precision as dp

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    qty_available = fields.Float(string='Cant disponible', compute='_compute_qty_available', store=False)
    
    margin_disp = fields.Float(compute='_product_margin_disp', digits=dp.get_precision('Product Price'), store=False)
    price_tax_disp = fields.Monetary(compute='_compute_amount_disp', string='Imp precio', readonly=True, store=False)
    price_total_disp = fields.Monetary(compute='_compute_amount_disp', string='Total precio', readonly=True, store=False)
    price_subtotal_disp = fields.Monetary(compute='_compute_amount_disp', string='Total disp', readonly=True, store=False)    
    product_uom_qty = fields.Float(digits=(16,0), default=1)
    desc_price_unit = fields.Float()
    base_price_unit = fields.Float()

    @api.onchange('product_uom_qty', 'product_uom', 'route_id')
    def _onchange_product_id_check_availability(self):
        if not self.product_id or not self.product_uom_qty or not self.product_uom:
            self.product_packaging = False
        return {}
    
    def _product_margin_disp(self):
        if not self.env.in_onchange:
            # prefetch the fields needed for the computation
            self.read(['price_subtotal_disp', 'purchase_price', 'qty_available', 'order_id'])
        for line in self:
            currency = line.order_id.pricelist_id.currency_id
            price = line.purchase_price
            line.margin_disp = currency.round(line.price_subtotal_disp - (price * line.qty_available))

    def _compute_qty_available(self):
        for line in self:
            qty_available = line.product_id.qty_available - line.product_id.outgoing_qty
            if qty_available < 0:
                line.qty_available = 0
            elif qty_available <= line.product_uom_qty:
                line.qty_available = qty_available
            elif qty_available > line.product_uom_qty:
                line.qty_available = line.product_uom_qty

    def _compute_amount_disp(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.qty_available, product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax_disp': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total_disp': taxes['total_included'],
                'price_subtotal_disp': taxes['total_excluded'],
            })


class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    margin_disp = fields.Monetary(compute='_product_margin_disp', currency_field='currency_id', digits=dp.get_precision('Product Price'), store=False)
    margin_porciento = fields.Float(compute='_product_margin_porc', digits=dp.get_precision('Product Price'), store=False)
    margin_porciento_disp = fields.Float(compute='_product_margin_disp', digits=dp.get_precision('Product Price'), store=False)
    amount_untaxed_disp = fields.Monetary(string='Base imponible', store=False, readonly=True, compute='_amount_all_disp')
    amount_tax_disp = fields.Monetary(string='Impuestos', store=False, readonly=True, compute='_amount_all_disp')
    amount_total_disp = fields.Monetary(string='Total', store=False, readonly=True, compute='_amount_all_disp')

    back_order_id = fields.Many2one('sale.order.backorder', string="Backorder generado", readonly=True)
    back_order_origin_id = fields.Many2one('sale.order.backorder', string="Backorder origen", readonly=True)
    transport_company_id = fields.Many2one('res.partner')

    def _product_margin_porc(self):
        for order in self:
            order.margin_porciento = order.margin/order.amount_untaxed*100 if order.amount_untaxed>0 else 0

    def _product_margin_disp(self):
        for order in self:
            if order.order_line:
                order.margin_disp = sum(order.order_line.filtered(lambda r: r.state != 'cancel').mapped('margin_disp'))
                order.margin_porciento_disp = order.margin_disp/order.amount_untaxed_disp*100 if order.amount_untaxed_disp>0 else 0
       
    def _amount_all_disp(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed_disp = amount_tax_disp = 0.0
            for line in order.order_line:
                amount_untaxed_disp += line.price_subtotal_disp
                amount_tax_disp += line.price_tax_disp
            order.amount_untaxed_disp = amount_untaxed_disp
            order.amount_tax_disp = amount_tax_disp
            order.amount_total_disp = amount_untaxed_disp + amount_tax_disp

    def action_confirm(self):
        # Validación única de cantidades
        if any(line.product_uom_qty <= 0 for line in self.order_line):
            raise exceptions.UserError("La cantidad del producto de todas las líneas debe ser mayor a cero.")
        self.back_order_id = False
        shortage_lines = self.order_line.filtered(lambda l: l.qty_available < l.product_uom_qty)
        if shortage_lines and self.env.context.get('origin_backorder')!=1:
            backorder_id = self.env['sale.order.backorder'].create({
                'sale_order_origin_id': self.id,
                'partner_id': self.partner_id.id,
                'company_id': self.company_id.id,
                'pricelist_id': self.pricelist_id.id,
                'partner_invoice_id': self.partner_invoice_id.id,
                'partner_shipping_id': self.partner_shipping_id.id,
                'payment_term_id': self.payment_term_id.id,
                'transport_company_id': self.transport_company_id.id if self.transport_company_id else False
            })
            self.back_order_id = backorder_id.id            
            model_line = self.env['sale.order.backorder.line']
            for line in shortage_lines:
                cant_pendiente = line.product_uom_qty - line.qty_available
                line.product_uom_qty = line.qty_available
                model_line.create({
                    'product_id': line.product_id.id,
                    'product_uom_qty': cant_pendiente,
                    'discount': line.discount,
                    'price_unit': line.price_unit,
                    'backorder_id': backorder_id.id                    
                })           
        
        # Check if there are lines with product_uom_qty > 0
        valid_lines = self.order_line.filtered(lambda line: line.product_uom_qty > 0)
        res = True
        if valid_lines:            
            # Remove lines with product_uom_qty == 0
            zero_lines = self.order_line.filtered(lambda line: line.product_uom_qty == 0)
            if zero_lines:
                zero_lines.unlink()
            res=super(SaleOrder,self).action_confirm()
        if self.back_order_id:
            self.message_post(body="Se ha generado un backorder para el pedido %s." % self.name)
        return res
    
    def _get_tax_amount_by_group_disp(self):
        self.ensure_one()
        res = {}
        for line in self.order_line:
            price_reduce = line.price_unit * (1.0 - line.discount / 100.0)
            taxes = line.tax_id.compute_all(price_reduce, quantity=line.qty_available, product=line.product_id, partner=self.partner_shipping_id)['taxes']
            for tax in line.tax_id:
                group = tax.tax_group_id
                res.setdefault(group, {'amount': 0.0, 'base': 0.0})
                for t in taxes:
                    if t['id'] == tax.id or t['id'] in tax.children_tax_ids.ids:
                        res[group]['amount'] += t['amount']
                        res[group]['base'] += t['base']
        res = sorted(res.items(), key=lambda l: l[0].sequence)
        res = [(l[0].name, l[1]['amount'], l[1]['base'], len(res)) for l in res]
        return res
    