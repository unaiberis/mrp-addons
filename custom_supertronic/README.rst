.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=========================
Custom Supertronic Module
=========================

Summary
=======

The **Custom Supertronic** module adds additional fields for verification and preparation to manufacturing orders and related tasks in Odoo.

Functionality
=============

1. **Project Task Enhancements**:
   - Adds fields for `Verification by` and `Preparation` to project tasks, related to the manufacturing order's product.
   - These fields are editable and update based on the associated manufacturing order's product settings.

2. **Product Template Enhancements**:
   - Adds a `Verification by` selection field to products with options such as:
     - Not Verified
     - Sent
     - By Prototype
     - By Age
     - By Plan
   - Adds a `Preparation` selection field to products with options such as:
     - Closed Box
     - Open Box
     - Only Bodies
     - Only Lids
     - Only Fronts
     - No Preparation

Installation
============

This module requires Odoo dependencies:
- MRP
- Project
- Project MRP

Install the module via the Odoo Apps interface.

Bug Tracker
===========

Report bugs or provide feedback on `GitHub Issues <https://github.com/avanzosc/custom-supertronic/issues>`_.

Credits
=======

Author
------
- Unai Beristain <unaiberistain@avanzosc.es>

License
=======

- License: AGPL-3.0 or later

Do not contact contributors directly about support or help with technical issues.
