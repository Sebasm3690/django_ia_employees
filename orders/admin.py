from django.contrib import admin
from .models import Order, Product, RefundRequest  

class Productdmin(admin.ModelAdmin):
  list_display = ['name','price','category','in_stock']

class OrderAdmin(admin.ModelAdmin):
  list_display = ['user','product_name','amount','status','status','carrier','tracking_number']

class RefundReuqestAdmin(admin.ModelAdmin):
  list_display = ['order','user','reason','status','created_at']

admin.site.register(Order, OrderAdmin)
admin.site.register(Product, Productdmin)
admin.site.register(RefundRequest, RefundReuqestAdmin)