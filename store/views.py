from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated,AllowAny
from django.contrib.auth.models import User
from .serializers import RegisterSerializer,UserSerializer
from rest_framework import status
from .models import Product, Category,Cart,CartItem,Order,OrderItem
from .serializers import ProductSerializer,CategorySerializer,CartItemSerializer,CartSerializer
from django.db.models import Q
from django.core.cache import cache

# Create your views here.

@api_view(['GET'])
def get_products(request):

    cache_key = f"products_{request.GET.urlencode()}"

    cached_data =cache.get(cache_key)
    if cached_data:
        return Response(cached_data)

    #all products
    products =Product.objects.all()

    # CATEGORY FILTER
    category_id = request.GET.get("category")
    
    
    if category_id:
        products =products.filter(category_id=category_id)
    
    #Search
    search = request.GET.get("search")

    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )

    #MIN price

    min_price = request.GET.get("min_price")

    if min_price:
        products = products.filter(price__gte =min_price)

    #Max price

    max_price = request.GET.get("max_price")

    if max_price:
        products = products.filter(price__lte =max_price)
    
    serializer= ProductSerializer(products, many=True)
    cache.set(cache_key, serializer.data, timeout=60 * 5)
    return Response(serializer.data)



@api_view(['GET'])
def get_product(request,pk):

    cache_key = f"product_{pk}"
    cached_data = cache.get(cache_key)

    if cached_data:
        return Response(cached_data)
    try:
        product=Product.objects.get(id=pk)
        serializer=ProductSerializer(product,context ={'request':request})
        cache.set(cache_key, serializer.data, timeout=60 * 10)
        return Response(serializer.data)
    except Product.DoesNotExist:
        return Response({'error':'Product not found'}, status=404)
@api_view(['GET'])
def get_categories(request):
    cached_data = cache.get("all_categories")

    if cached_data:
        return Response(cached_data)
    categories= Category.objects.all()
    serializer = CategorySerializer(categories,many=True)
    cache.set("all_categories", serializer.data, timeout=60 * 60)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_cart(request):
    cart,created = Cart.objects.get_or_create(user=request.user)
    serializer = CartSerializer(cart)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    product_id = request.data.get('product_id')

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response(
            {"error": "Product not found"},
            status=404
        )
    
    cart,created = Cart.objects.get_or_create(user=request.user)
    item, created = CartItem.objects.get_or_create(cart=cart,product=product)

    if not created:
        item.quantity+=1
        item.save()
    return Response({'message': 'Product added to cart', "cart":CartSerializer(cart).data})   

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_cart_quantity(request):
    item_id = request.data.get('item_id')
    quantity= request.data.get('quantity')
    if not item_id or quantity is None:
        return Response({'error':'Item ID and quantity are required'},status=400)
    
    try:
        item = CartItem.objects.get(id=item_id, cart__user=request.user)
        if int(quantity)<1:
            item.delete()
            return Response({'error': 'Quantity must be at least 1'},status=400)
        
        item.quantity = int(quantity)
        item.save()
        serializer=CartItemSerializer(item)
        return Response(serializer.data)
    except CartItem.DoesNotExist:
        return Response({'error':'Cart item not found'},status=404)
    
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_from_cart(request):
    item_id = request.data.get('item_id')
    CartItem.objects.filter(id=item_id, cart__user=request.user).delete()
    return Response({'message': 'Item remove from cart'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order(request):
    try:
        data =request.data
        name=data.get('name')
        address=data.get('address')
        phone=data.get('phone')
        payment_method=data.get('payment_method','COD')

        #valid phone number
        if not phone.isdigit() or len(phone)<10:
            return Response({'error':'Invalid phone number'}, status=400)
        

        #get user cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        if not cart.items.exists():
            return Response({'error':'Cart is empty'}, status=400)
        
        total = sum([float(item.product.price) * item.quantity for item in cart.items.all()])

        #create order
        order =Order.objects.create(user = request.user,total_amount=total)


        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )

        #Clear cart
        cart.items.all().delete()
        
        return Response({'message':'Order created successfully','order_id': order.id}) 

    except Exception as e:
        return Response({'error': str(e)}, status=500)    

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user=serializer.save()
        return Response({"message":"User created successfully","user":UserSerializer(user).data},status=status.HTTP_201_CREATED)
    return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
