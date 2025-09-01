from odoo import api, fields, models, exceptions
from datetime import datetime, time
from odoo.addons import decimal_precision as dp
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError


class SaleOrderBackorder(models.Model):
    _name = "sale.order.backorder"
    _order = "date desc, id desc"

    name = fields.Char(compute='_compute_name', store=False, string="Número")
    sale_order_origin_id = fields.Many2one('sale.order', string="Pedido de venta origen", readonly=True, required=True)
    sale_order_generada_ids = fields.One2many('sale.order', 'back_order_origin_id', string="Pedidos de venta generado", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Cliente", readonly=True, related="sale_order_origin_id.partner_id")
    date = fields.Date(string="Fecha", required=True, default=fields.Date.context_today)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('cancel', 'Cancelado'),], string='Estado', readonly=True, default='draft', tracking=True)
    company_id = fields.Many2one('res.company', 'Compañía', default=lambda self: self.env['res.company']._company_default_get('sale.order'))
    line_ids = fields.One2many('sale.order.backorder.line', 'backorder_id', string='Order Lines', states={'cancel': [('readonly', True)], 'confirmed': [('readonly', True)]}, copy=True, auto_join=True)
    currency_id = fields.Many2one("res.currency", related='pricelist_id.currency_id', string="Moneda", readonly=True, required=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Lista de precios', required=True, readonly=True)
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all', track_visibility='always')

    partner_invoice_id = fields.Many2one('res.partner', string='Dirección de Factura', readonly=True, required=True, states={'draft': [('readonly', False)]})
    partner_shipping_id = fields.Many2one('res.partner', string='Dirección de Entrega', readonly=True, required=True, states={'draft': [('readonly', False)]})
    payment_term_id = fields.Many2one('account.payment.term', string='Plazos de pago')
    transport_company_id = fields.Many2one('res.partner', string='Empresa de transporte')
    fecha_prevista = fields.Date(
        string='Fecha prevista',
        store=True,
        compute='_compute_fecha_prevista'
    )

    def _compute_name(self):
        for record in self:
            if record.id:
                record.name = 'BO' + str(record.id).zfill(5)
            else:
                record.name = False

    @api.depends('line_ids.date_prev')
    def _compute_fecha_prevista(self):
        for order in self:
            fechas = order.line_ids.filtered(lambda r: r.product_qty_confirmed > 0).mapped('date_prev')
            fecha_prevista = min(fechas) if fechas else False
            order.fecha_prevista = fields.Datetime.from_string(fecha_prevista) if fecha_prevista else False

    @api.depends('line_ids.price_subtotal')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = 0.0
            for line in order.line_ids:
                amount_untaxed += line.price_subtotal
            order.update({
                'amount_total': amount_untaxed,
            })

    def action_cancel_backorder(self):
        self.state = 'cancel'
        return True
       
    def action_confirm_backorder(self):
        # Filtrar líneas con cantidad confirmada
        lines_confirmed = [line for line in self.line_ids if line.product_qty_confirmed > 0]
        if not lines_confirmed:
            raise exceptions.ValidationError("No hay cantidad confirmada.")

        # Agrupar líneas por fechas previstas con diferencia máxima de 10 días
        grouped_lines = []
        sorted_lines = sorted(lines_confirmed, key=lambda l: fields.Datetime.from_string(l.date_prev))
        current_group = [sorted_lines[0]]

        for line in sorted_lines[1:]:
            current_date = fields.Datetime.from_string(line.date_prev)
            group_date = fields.Datetime.from_string(current_group[-1].date_prev)
            if (current_date - group_date).days <= 10:
                current_group.append(line)
            else:
                grouped_lines.append(current_group)
                current_group = [line]
        grouped_lines.append(current_group)

        # Crear órdenes de venta para cada grupo
        for group in grouped_lines:
            sale_order_id = self.env['sale.order'].create({
                'partner_id': self.partner_id.id,
                'company_id': self.company_id.id,
                'pricelist_id': self.pricelist_id.id,
                'partner_invoice_id': self.partner_invoice_id.id,
                'partner_shipping_id': self.partner_shipping_id.id,
                'payment_term_id': self.payment_term_id.id,
                'back_order_origin_id': self.id,
                'transport_company_id': self.transport_company_id.id if self.transport_company_id else False
            })
            for line in group:
                self.env['sale.order.line'].create({
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_qty_confirmed,
                    'discount': line.discount,
                    'price_unit': line.price_unit,
                    'order_id': sale_order_id.id
                })
            group_len = len(group)
            if group[group_len-1].date_prev:
                # Zona horaria del usuario
                local_tz = pytz.timezone(self.env.user.partner_id.tz)
                # 1. Crear el datetime en la zona local
                dt_local = local_tz.localize(datetime.strptime(group[group_len-1].date_prev + ' 00:00:00', DEFAULT_SERVER_DATETIME_FORMAT))

                # 2. Convertir a UTC
                dt_utc = dt_local.astimezone(pytz.utc)

                # 3. Guardar en el campo Datetime (en UTC)
                sale_order_id.requested_date = fields.Datetime.to_string(dt_utc)
            ctx = dict(self._context, origin_backorder=1)
            sale_order_id.with_context(ctx).action_confirm()
            """ picking = self.env['stock.picking'].search([('sale_id', '=', sale_order_id.id)], limit=1)
            if picking:
                picking.state = 'assigned' """

        self.state = 'confirmed'
        return True

class SaleOrderBackorderLine(models.Model):
    _name = "sale.order.backorder.line"

    backorder_id = fields.Many2one('sale.order.backorder', string="Backorder", required=True, ondelete='cascade', index=True, copy=False)
    discount = fields.Float(string='Desc (%)', digits=dp.get_precision('Discount'), default=0.0)
    product_id = fields.Many2one('product.product', string='Producto', domain=[('sale_ok', '=', True)], change_default=True, ondelete='restrict', required=True)
    virtual_available = fields.Float(related="product_id.virtual_available")
    product_uom_qty = fields.Integer(string='Cant. ped', required=True, readonly=True)
    product_uom_dispon = fields.Float(string='Cant. disp', compute='_compute_date_disp', store=False, default=0.0)
    date_prev = fields.Date(string="Fecha prevista", compute='_compute_date_prev', store=False)        
    product_qty_prev = fields.Integer(string='Cantidad', compute='_compute_date_prev', store=False, default=0.0)
    product_qty_confirmed = fields.Integer(string='Cant. confirmada', required=True, default=0.0)
    price_base = fields.Float('Precio base', required=True, digits=dp.get_precision('Product Price'), default=0.0)
    price_unit = fields.Float('Precio unitario', required=True, digits=dp.get_precision('Product Price'), default=0.0)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    currency_id = fields.Many2one("res.currency", related='backorder_id.pricelist_id.currency_id', string="Moneda", readonly=True, required=True)
    company_id = fields.Many2one('res.company', 'Compañía', default=lambda self: self.env['res.company']._company_default_get('sale.order'))

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('sales_team.group_sale_manager'):
            raise UserError('Usted no tiene permiso para eliminar')
        return super(SaleOrderBackorderLine, self).unlink()
    
    @api.onchange('price_unit')
    def _onchange_price_unit(self):
        if not self.env.user.has_group('sales_team.group_sale_manager'):
            raise UserError('Usted no tiene permiso para modificar el precio unitario.')
    
    def _compute_date_disp(self):
        for line in self:
            product_uom_dispon =  line.product_id.qty_available - line.product_id.outgoing_qty
            line.product_uom_dispon = product_uom_dispon if product_uom_dispon > 0 else 0

    def _compute_date_prev(self):
        for line in self:
            line.product_qty_prev = 0
            if line.product_id and line.backorder_id:
                move = self.env['purchase.order.line'].search([
                    ('order_id.state', '=', 'purchase'),
                    ('product_id', '=', line.product_id.id),
                    ('date_planned', '>=', line.backorder_id.date)
                ], order='date_planned asc', limit=1)
                if move:
                    line.date_prev = move.date_planned
                    line.product_qty_prev = move.product_qty
                else:
                    line.date_prev = False
                    line.product_qty_prev = 0          

    @api.onchange('product_qty_confirmed', 'virtual_available')
    def _onchange_product_qty_confirmed(self):
        for line in self:
            if line.product_qty_confirmed > line.virtual_available:
                raise exceptions.ValidationError("La cantidad confirmada no puede ser mayor a la cantidad prevista.")
            if line.product_qty_confirmed < 0:
                raise exceptions.ValidationError("La cantidad confirmada no puede ser negativa.")

    @api.depends('product_qty_confirmed', 'discount', 'price_unit')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            line.price_subtotal = price * line.product_qty_confirmed
        
