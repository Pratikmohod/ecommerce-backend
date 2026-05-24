from rest_framework import serializers
from .models import Product, Category,Cart,CartItem
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    category=CategorySerializer(read_only=True)
    class Meta:
        model = Product   
        fields = '__all__'  


class CartItemSerializer(serializers.ModelSerializer):
    product_name=serializers.CharField(source='product.name',read_only=True)
    product_price=serializers.DecimalField(source='product.price',max_digits=10,decimal_places=2,read_only=True)
    product_image=serializers.ImageField(source='product.image',read_only=True)

    class Meta:
        model = CartItem
        fields = '__all__'
        
class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True,read_only=True)
    total = serializers.ReadOnlyField()

    class Meta:
        model=Cart
        fields='__all__'     


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id','username', 'email']  


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model =User
        fields = ['username','email','password','password2']
        
    def validate(self,data):
        # Password match validation
        if data['password'] != data['password2']:
            raise serializers.ValidationError({
                "password" : "Passwords do not match."
            })
        
        #username already exist
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({
                 "username": "Username already exists."
            })
        
        # Email already exists
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({
                "email":"Email already exists."
            })
        
        #Strong password validation
        try:
            validate_password(data['password'])
        except ValidationError as e:
            raise serializers.ValidationError({
                "password": list(e.message)
            })    

        return data
        
    def create(self,validated_data):
        validated_data.pop('password2')

        username = validated_data['username']
        email=validated_data.get('email','')
        password = validated_data['password']
        user = User.objects.create_user(username=username,email=email,password=password)
        return user



     