# Copyright 2023 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
{
    "name": "Jvv Product Supplierinfo Certifications",
    "summary": "Customization Module",
    "version": "8.0.2.0.0",
    "category": "Custom Module",
    "license": "AGPL-3",
    "author": "AvanzOSC",
    "website": "https://github.com/avanzosc/mrp-addons",
    "contributors": [
        "Ana Juaristi <anajuaristi@avanzosc.es>",
        "Alfredo de la Fuente <alfredodelafuente@avanzosc.es>",
    ],
    "depends": [
        "product",
        "purchase",
        "product_by_supplier",
        "jvv_custom",
        "procurement",
        "stock",
        "product_supplierinfo_view",
        "product_supplierinfo_for_customer",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/product_supplierinfo_certification_views.xml",
        "views/product_supplierinfo_views.xml",
        "views/procurement_order_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
}
