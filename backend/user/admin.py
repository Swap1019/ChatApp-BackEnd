from django.contrib import admin
from .models import User

# Register your models here.
class UserAdmin(admin.ModelAdmin):
    list_display = ('id','username','email','is_staff','is_active',)
    

admin.site.register(User,UserAdmin)
