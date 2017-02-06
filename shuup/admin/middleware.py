# -*- coding: utf-8 -*-
# This file is part of Shuup.
#
# Copyright (c) 2012-2017, Shoop Commerce Ltd. All rights reserved.
#
# This source code is licensed under the OSL-3.0 license found in the
# LICENSE file in the root directory of this source tree.
from django.conf import settings
from django.contrib.auth.signals import user_logged_out
from django.core.exceptions import ImproperlyConfigured

from shuup.core.models import Shop


class ShuupAdminMiddleware(object):
    def process_request(self, request):
        user = request.user
        is_superuser = getattr(user, "is_superuser", False)
        is_staff = getattr(user, "is_staff", False)
        if not (is_staff or is_superuser):
            return

        if not request.session.get("admin_shop"):
            queryset = Shop.objects
            if not is_superuser:
                queryset = queryset.filter(staff_members=request.user)
            request.session.setdefault("admin_shop", queryset.first())
        if not request.session.get("admin_shops"):
            queryset = Shop.objects.all()
            if not is_superuser:
                queryset = queryset.filter(staff_members=request.user)
            request.session.setdefault("admin_shops", queryset)

        active_shop = request.session.get("admin_shop")
        if active_shop:
            active_shop_id = active_shop.id
        else:
            active_shop_id = None

        if not is_superuser and Shop.objects.filter(
                id=active_shop_id, staff_members__id=request.user.id).exists():
            raise ImproperlyConfigured("The user is not linked to the current shop correctly.")

    @classmethod
    def refresh_on_logout(cls, request, **kwargs):
        request.session.pop("admin_shops", None)


if (
    "django.contrib.auth" in settings.INSTALLED_APPS and
    "shuup.admin.middleware.ShuupAdminMiddleware" in settings.MIDDLEWARE_CLASSES
):
    user_logged_out.connect(ShuupAdminMiddleware.refresh_on_logout, dispatch_uid="shuup_admin_refresh_on_logout")
