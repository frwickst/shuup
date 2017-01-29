# -*- coding: utf-8 -*-
# This file is part of Shuup.
#
# Copyright (c) 2012-2017, Shoop Commerce Ltd. All rights reserved.
#
# This source code is licensed under the OSL-3.0 license found in the
# LICENSE file in the root directory of this source tree.
from __future__ import unicode_literals

from collections import defaultdict, OrderedDict

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as PermissionGroup
from django.contrib.auth.models import Permission
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from shuup.admin.forms.fields import Select2MultipleField
from shuup.admin.module_registry import get_modules
from shuup.admin.utils.permissions import (
    get_permission_object_from_string, get_permissions_from_urls
)
from shuup.admin.utils.views import CreateOrUpdateView


class PermissionGroupForm(forms.ModelForm):
    class Meta:
        model = PermissionGroup
        exclude = ("permissions",)

    def __init__(self, *args, **kwargs):
        super(PermissionGroupForm, self).__init__(*args, **kwargs)
        initial_permissions = self._get_initial_permissions()
        self.fields["name"].help_text = _("The permission group name.")
        initial_members = self._get_initial_members()
        members_field = Select2MultipleField(
            model=get_user_model(),
            initial=[member.pk for member in initial_members],
            required=False,
            label=_("Members"),
            help_text=_(
                "Set the users that belong to this permission group."
            )
        )
        members_field.widget.choices = [(member.pk, force_text(member)) for member in initial_members]
        self.fields["members"] = members_field

        permission_code_to_name = {}
        for permission in Permission.objects.all():
            permission_code_to_name[
                "%s.%s" % (permission.content_type.app_label, permission.codename)] = permission.name

        self.module_permissions = defaultdict(list)
        for module in self._get_module_choices():
            for module_permission in get_permissions_from_urls(module.get_urls()):
                field = forms.BooleanField(
                    initial=bool(module_permission == initial_permissions),
                    label=permission_code_to_name[module_permission],
                    required=False
                )
                self.module_permissions[module.name].append(module_permission)
                self.fields[module_permission] = field

    def get_module_permissions(self):
        return OrderedDict(sorted(self.module_permissions.items()))

    def _get_module_choices(self):
        return [m for m in get_modules() if m.name != "_Base_"]

    def _get_initial_members(self):
        if self.instance.pk:
            return self.instance.user_set.all()
        else:
            return []

    def _get_initial_permissions(self):
        permissions = set()
        if self.instance.pk:
            for perm in self.instance.permissions.all():
                name, module, _ = perm.natural_key()
                permissions.add("%s.%s" % (module, name))
        return permissions

    def clean_members(self):
        members = self.cleaned_data.get("members", [])

        return get_user_model().objects.filter(pk__in=members).all()

    def clean(self):
        cleaned_data = super(PermissionGroupForm, self).clean()

        permissions = set()
        modules = cleaned_data.pop("modules", [])
        required_permissions = self._get_required_permissions(modules)

        for permission in required_permissions:
            permissions.add(get_permission_object_from_string(permission))

        cleaned_data["required_permissions"] = permissions

        return cleaned_data

    def save(self):
        obj = super(PermissionGroupForm, self).save()
        obj.permissions = set(self.cleaned_data["required_permissions"])
        obj.user_set = set(self.cleaned_data["members"])
        return obj


class PermissionGroupEditView(CreateOrUpdateView):
    model = PermissionGroup
    form_class = PermissionGroupForm
    template_name = "shuup/admin/permission_groups/edit.jinja"
    context_object_name = "permission_group"
    add_form_errors_as_messages = True
