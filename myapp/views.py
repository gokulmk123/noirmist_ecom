# views.py
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import login,logout,get_backends
from .forms import AdminLoginForm,UserSignupForm,UserLoginForm
from django.views.decorators.cache import never_cache
from django.core.mail import send_mail
from django.conf import settings

from django.contrib import messages
import random
from . models import CustomUser,Product,Category,Brand,ProductImage,ProductVariant,banner
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.http import JsonResponse
from datetime import date
from django.core.paginator import Paginator



@never_cache
def admin_login_view(request):
    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect('user_login')
    
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')

    

    if request.method == 'POST':
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            user = form.user
            # 🛠️ Set the backend manually
            backends = get_backends()
            user.backend = f"{backends[0].__module__}.{backends[0].__class__.__name__}"

            login(request, user)
            request.session['adminuser'] = user.username
            return redirect('admin_dashboard')
    else:
        form = AdminLoginForm()

    return render(request, 'admin_signin.html', {'form': form})

@never_cache
def admin_logout(request):
    if request.method == 'POST':
        logout(request)
        request.session.flush()  # Clears session data
        return redirect('admin_login')

@never_cache
def admin_dashboard(request):
    if request.session.get('user'):
        return redirect('home')
    if not request.session.get('adminuser'):
        return redirect('admin_login')
    
    total_customers = CustomUser.objects.filter(is_superuser=False).count()
        
    total_product= Product.objects.exclude(status='Listed').count()
            
    return render(request, 'dashboard.html',{
        'key1':total_customers,'key2':total_product})


@never_cache
def admin_customers_view(request):
    if not request.session.get('adminuser'):
        return redirect('admin_login')

    # Toggle block/unblock
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        user = get_object_or_404(CustomUser, id=user_id, is_superuser=False)
        user.is_active = not user.is_active
        user.save()
        return redirect('admin_customers')

    # Search
    query = request.GET.get('q', '')
    customers = CustomUser.objects.filter(is_superuser=False)
    if query:
        customers = customers.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query)
        )

    # ✅ Pagination
    paginator = Paginator(customers, 10)  # 10 customers per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_customer.html', {
        'customers': page_obj,
        'search_query': query,
        'page_obj': page_obj,  # Needed for pagination template logic
    })

@never_cache
def admin_product(request):
    if not request.session.get('adminuser'):
        return redirect('admin_login')

    show_deleted = request.GET.get('show') == 'deleted'
    search_query = request.GET.get('q', '')

    products = Product.objects.prefetch_related('variants', 'productimage_set').filter(is_deleted=show_deleted)

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

    #  Assign main image BEFORE pagination
    product_list = []
    for product in products:
        main_image = product.productimage_set.filter(is_main=True).first()
        if not main_image:
            main_image = product.productimage_set.first()
        product.main_image = main_image
        product_list.append(product)

    # Pagination
    paginator = Paginator(product_list, 10)  # 10 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_product.html', {
        'products': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'show_deleted': show_deleted
    })

def toggle_product_status(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.status = 'unlisted' if product.status == 'listed' else 'listed'
    product.save()
    return redirect('admin_product')

def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_deleted = True
    product.status = 'unlisted'
    product.save()
    return redirect('admin_product')

def recover_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_deleted=True)
    product.is_deleted = False
    product.save()
    return redirect('admin_product')

def addproduct(request):
    edit_id = request.GET.get('edit') or request.POST.get('edit')
    product = None
    variants = []

    if edit_id:
        product = get_object_or_404(Product, id=edit_id)
        variants = ProductVariant.objects.filter(product_id=product)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()

        # Name validation
        if not name:
            messages.error(request, 'Product name is required.')
            return redirect(f"{request.path}?edit={edit_id}" if edit_id else request.path)

        if not edit_id and Product.objects.filter(name__iexact=name).exists():
            messages.error(request, 'Product name already exists.')
            return redirect(request.path)

        # Category validation
        try:
            category_id = int(request.POST.get('category_id'))
            category = Category.objects.get(category_id=category_id, is_deleted=False, status='Listed')
        except (ValueError, Category.DoesNotExist):
            messages.error(request, 'Please select a valid category.')
            return redirect(f"{request.path}?edit={edit_id}" if edit_id else request.path)

        # Brand validation
        try:
            brand_id = int(request.POST.get('brand_id'))
            brand = Brand.objects.get(brand_id=brand_id, is_deleted=False, status='Listed')
        except (ValueError, Brand.DoesNotExist):
            messages.error(request, 'Please select a valid brand.')
            return redirect(f"{request.path}?edit={edit_id}" if edit_id else request.path)

        description = request.POST.get('description', '')

        # Create or update product
        if edit_id:
            product.name = name
            product.description = description
            product.category_id = category
            product.brand_id = brand
            product.save()
        else:
            product = Product.objects.create(
                name=name,
                description=description,
                default_price=0,
                default_stock=0,
                image_url='default.jpg',
                category_id=category,
                brand_id=brand,
            )

        # Delete old variants on edit
        if edit_id:
            ProductVariant.objects.filter(product_id=product).delete()

        # --- Variant Validation ---
        variants_input = request.POST.getlist('variants[]')
        valid_variants = []

        for variant in variants_input:
            try:
                size, price, stock = variant.split('|')
                size = size.strip()
                price = float(price)
                stock = int(stock)

                if not size or price < 0 or stock < 0:
                    raise ValueError("Invalid variant values")

                valid_variants.append({
                    'size': size,
                    'price': price,
                    'stock': stock
                })

            except Exception as e:
                print('Variant error:', e)
                messages.error(request, 'One or more product variants are invalid. Please check the inputs.')
                return redirect(f"{request.path}?edit={edit_id}" if edit_id else request.path)

        if not valid_variants:
            messages.error(request, 'At least one valid variant is required.')
            return redirect(f"{request.path}?edit={edit_id}" if edit_id else request.path)

        for var in valid_variants:
            ProductVariant.objects.create(
                product_id=product,
                size=var['size'],
                price=var['price'],
                stock=var['stock']
            )

        # --- Save Images ---
        images = request.FILES.getlist('variantImages')
        for idx, img in enumerate(images):
            ProductImage.objects.create(
                product_id=product,
                image=img,
                alt_text=f"{name} - Image {idx + 1}",
                is_main=(idx == 0)
            )

        messages.success(request, 'Product saved successfully.')
        return redirect('admin_product')

    # --- Load form ---
    categories = Category.objects.filter(is_deleted=False, status='Listed')
    brands = Brand.objects.filter(is_deleted=False, status='Listed')

    return render(request, 'admin_addproduct.html', {
        'categories': categories,
        'brands': brands,
        'product': product,
        'variants': variants,
        'is_edit': bool(edit_id),
    })

def get_form_context(product, variants, edit_id):
    return {
        'categories': Category.objects.filter(is_deleted=False, status='Listed'),
        'brands': Brand.objects.filter(is_deleted=False, status='Listed'),
        'product': product,
        'variants': variants,
        'is_edit': bool(edit_id),
    }

def admin_category(request):
    if request.method == 'POST':
        if 'edit_category_id' in request.POST:
            category_id = request.POST.get('edit_category_id')
            category = get_object_or_404(Category, category_id=category_id)
            name = request.POST.get('edit_name')
            description = request.POST.get('edit_description')

            if Category.objects.exclude(pk=category_id).filter(name__iexact=name, is_deleted=False).exists():
                messages.error(request, 'Another category with this name already exists.')
            else:
                category.name = name
                category.description = description
                category.updated_at = timezone.now()
                category.save()
                messages.success(request, 'Category updated successfully.')
        else:
            name = request.POST.get('name')
            description = request.POST.get('description')

            existing_category = Category.objects.filter(name__iexact=name).first()
            if existing_category:
                if existing_category.is_deleted:
                    existing_category.is_deleted = False
                    existing_category.description = description
                    existing_category.status = 'Listed'
                    existing_category.save()
                    messages.success(request, 'Category restored successfully.')
                else:
                    messages.error(request, 'Category already exists.')
            else:
                Category.objects.create(name=name, description=description)
                messages.success(request, 'Category added successfully.')

        return redirect('admin_category')

    categories = Category.objects.filter(is_deleted=False).order_by('category_id')

    # Add pagination (10 per page)
    paginator = Paginator(categories, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_category.html', {
        'categories': page_obj.object_list,
        'page_obj': page_obj
    })

def toggle_category_status(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    category.status = 'Unlisted' if category.status == 'Listed' else 'Listed'
    category.updated_at = timezone.now()
    category.save()
    return redirect('admin_category')

@csrf_exempt
def delete_category(request, category_id):
    category = get_object_or_404(Category, category_id=category_id)
    category.is_deleted = True
    category.save()
    return redirect('admin_category')



def admin_brand(request):
    if request.method == 'POST':
        brand_id = request.POST.get('brand_id')
        name = request.POST.get('name')
        description = request.POST.get('description')
        logo = request.FILES.get('logo')

        if brand_id:
            brand = get_object_or_404(Brand, pk=brand_id)
            if Brand.objects.exclude(pk=brand_id).filter(name__iexact=name, is_deleted=False).exists():
                messages.error(request, 'Another brand with this name already exists.')
            else:
                brand.name = name
                brand.description = description
                if logo:
                    brand.logo = logo
                brand.save()
                messages.success(request, 'Brand updated successfully.')
        else:
            if Brand.objects.filter(name__iexact=name, is_deleted=False).exists():
                messages.error(request, 'Brand already exists.')
            else:
                Brand.objects.create(name=name, description=description, logo=logo)
                messages.success(request, 'Brand added successfully.')
        return redirect('admin_brand')

    brand_list = Brand.objects.filter(is_deleted=False).order_by('brand_id')

    # Pagination
    paginator = Paginator(brand_list, 10)  # 10 brands per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_brand.html', {
        'brands': page_obj.object_list,
        'page_obj': page_obj
    })
def toggle_brand_status(request, brand_id):
    brand = get_object_or_404(Brand, pk=brand_id)
    brand.status = 'Unlisted' if brand.status == 'Listed' else 'Listed'
    brand.save()
    return redirect('admin_brand')

def delete_brand(request, brand_id):
    brand = get_object_or_404(Brand, pk=brand_id)
    brand.is_deleted = not brand.is_deleted
    brand.save()
    return redirect('admin_brand')

def admin_banner(request):
    
    if request.method == 'POST':
        banner_id = request.POST.get('banner_id')
        banner_name = request.POST.get('banner_name')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        description = request.POST.get('description')
        banner_img = request.FILES.get('banner_img')

        if not banner_name or not start_date or not end_date:
            messages.error(request, 'Please fill in all required fields.')
            return redirect('admin_banner')

        if banner_id:  # Update existing banner
            banner_obj = get_object_or_404(banner, id=banner_id)
            banner_obj.banner_name = banner_name
            banner_obj.start_date = start_date
            banner_obj.end_date = end_date
            banner_obj.description = description
            if banner_img:
                banner_obj.banner_img = banner_img
            banner_obj.save()
            messages.success(request, 'Banner updated successfully.')
        else:  # Add new banner
            banner.objects.create(
                banner_name=banner_name,
                banner_img=banner_img,
                start_date=start_date,
                end_date=end_date,
                description=description
            )
            messages.success(request, 'Banner added successfully.')

        return redirect('admin_banner')

    banners = banner.objects.all().order_by('end_date')
    for b in banners:
        b.days_left = (b.end_date - date.today()).days

    return render(request, 'admin_banner.html', {
        'banners': banners
    })