from django.contrib import admin

from .models import CMF, CMFCoefficient, CMFMetadata, CMFUserPermission


class CMFCoefficientInline(admin.TabularInline):
    model = CMFCoefficient
    extra = 0


class CMFUserPermissionInline(admin.StackedInline):
    model = CMFUserPermission
    extra = 0
    max_num = 1


class CMFMetadataInline(admin.StackedInline):
    model = CMFMetadata
    extra = 0
    max_num = 1


@admin.register(CMF)
class CMFAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'author', 'modified_at')
    search_fields = ('code', 'title', 'metadata__cmf_group1', 'metadata__descr_en_us', 'author__username')
    inlines = [CMFMetadataInline, CMFCoefficientInline, CMFUserPermissionInline]


@admin.register(CMFCoefficient)
class CMFCoefficientAdmin(admin.ModelAdmin):
    list_display = ('cmf', 'travel_mode', 'severity', 'coefficient_a', 'coefficient_b', 'coefficient_c')
    list_filter = ('travel_mode', 'severity')


@admin.register(CMFUserPermission)
class CMFUserPermissionAdmin(admin.ModelAdmin):
    list_display = ('cmf', 'crossroads', 'borough', 'ville', 'shire', 'provincia', 'comarca', 'metro', 'commonwealth', 'republic')
