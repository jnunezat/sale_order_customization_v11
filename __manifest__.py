# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Sale Order Customization',
    'version' : '1.0',
    'author':'',
    'category': 'Sales',
    'description': """

        Sale Order Customization

    """,
    'license': 'LGPL-3',
    'depends' : ['sale_margin', 'sale_order_dates', 'stock', 'go_home', 'purchase'],
    'data': [
        'views/sale_order_views.xml',
        'views/backorder_views.xml',
        'report/sale_report_templates.xml',
        'security/ir.model.access.csv'
    ],        
    'installable': True,
    'application': True,
    'auto_install': False

}
