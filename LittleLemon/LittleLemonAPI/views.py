from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Category, MenuItem, Cart, Order, OrderItem
from .serializers import CategorySerializer, MenuItemSerializer, CartSerializer, OrderSerializer, UserSerializer
from django.contrib.auth.models import User, Group
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404


# Create your views here.

class MenuItemView(generics.ListCreateAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['category', 'price', 'featured', 'title']
    ordering_fields = ['id', 'price', 'title']
    search_fields = ['category__title', 'title']

    def get(self, request):
        user = request.user
        menu_items = self.get_queryset()
        serializer = self.serializer_class(menu_items, many=True)
        if not user.groups.filter(name='Manager').exists():
            return Response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)
        
    def post(self, request):
        user = request.user
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            if user.groups.filter(name='Manager').exists():
                serializer.save()
                return Response({'message':'Created'}, status=status.HTTP_201_CREATED)
            else:
                return Response({'message':'You are not authorized'},status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SingleMenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated]

    def put(self, request, pk=None):
        user = request.user
        if user.groups.filter(name='Manager').exists():
            menu_item = get_object_or_404(self.get_object())
            serializer = self.serializer_class(menu_item, data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return Response({'message': 'Updated'}, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)
        
    def delete(self, request, pk=None):
        user = request.user
        if user.groups.filter(name='Manager').exists():
            menu_item = get_object_or_404(self.get_object())
            menu_item.delete()
            return Response({'message':'Deleted'}, status=status.HTTP_200_OK)
        else:
            return Response({'message':'You are not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
    def patch(self, request, pk=None):
        user = request.user
        if user.groups.filter(name='Manager').exists():
            menu_item = get_object_or_404(self.get_object())
            serializer = self.serializer_class(menu_item, data=request.data, partial=True)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return Response({'message': 'Updated'}, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'message': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
                            

class CartView(generics.ListCreateAPIView, generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer
    
    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)
    
    def List(self, request):
        user = request.user
        if user.groups.filter(name='Manager').exists() or user.groups.filter(name='Delivery Crew').exists():
            return Response(status= status.HTTP_403_FORBIDDEN)
        
    def create(self, request, *args, **kwargs):
        serialized_data = self.get_serializer(data=request.data)
        serialized_data.is_valid(raise_exception=True)
        menuitem = serialized_data.validated_data['menuitem']
        quantity = serialized_data.validated_data['quantity']
        serialized_data.validated_data['menuitem'] = menuitem
        serialized_data.validated_data['unit_price'] = menuitem.price
        serialized_data.validated_data['price'] = quantity * menuitem.price
        serialized_data.save(user=self.request.user)
        return Response(
            {'message': f'{menuitem.title} successfully added to the cart for {request.user.username}'},
            status.HTTP_201_CREATED
        )

    def delete(self, request, *args, **kwargs):
        self.get_queryset().delete()
        return Response(
            {'message': f'Cart successfully emptied for {request.user.username}'},
            status.HTTP_200_OK
        )
        

class OrderView(generics.ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.groups.filter(name='Manager').exists():
            return super().get_queryset()
        else:
            return Order.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        cart_items = Cart.objects.filter(user=request.user)
        if cart_items.exists():
            serialized_data = self.serializer_class(data=request.data)
            serialized_data.is_valid(raise_exception=True)
            serialized_data.save(user=request.user, total=0)  
            order = serialized_data.instance  
            total = 0
            for item in cart_items:
                order_item = OrderItem(
                    order=order,
                    menuitem=item.menuitem,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    price=item.price
                )
                order_item.save()
                total += item.price
            cart_items.delete()
            order.total = total
            order.save()
            return Response(
                {'message': f'Order successfully added'},
                status.HTTP_201_CREATED
            )

        return Response(
            {'message': f'There is no item in the cart!'},
            status.HTTP_400_BAD_REQUEST
        )
    

class SingleOrderView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def retrieve(self, request, *args, **kwargs):
        user = request.user
        if not request.user.groups.filter(name='Manager').exists() or not request.user.groups.filter(name='Delivery Crew').exists():
            item = get_object_or_404(self.queryset, pk=kwargs['pk'])
            if request.user == item.user:
                serialized_item = self.get_serializer(item)
                return Response(
                    serialized_item.data,
                    status.HTTP_200_OK
                )
            return Response(
                {'message': 'You do not have permission to see this page!'},
                status.HTTP_403_FORBIDDEN
            )
        return super().retrieve(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        user = request.user
        if request.user.groups.filter(name='Delivery Crew').exists():
            params = list(request.data.keys())
            if len(params) > 0 and params != ['status']:
                return Response(
                    {'message': 'You do not have permission to perform this action!'},
                    status.HTTP_403_FORBIDDEN
                )
        if request.user.groups.filter(name='Manager').exists():
            if request.data.get('delivery_crew'):
                delivery_crew_id = request.data['delivery_crew']
                try:
                    user = User.objects.get(id=delivery_crew_id)
                except User.DoesNotExist:
                    return Response(
                        {'message': f'The selected user does not exist'},
                        status.HTTP_400_BAD_REQUEST
                    )
                if not user.groups.filter(name='Delivery Crew').exists():
                    return Response(
                        {'message': f'The selected user is not a delivery crew'},
                        status.HTTP_400_BAD_REQUEST
                    )
        return super().partial_update(request, *args, **kwargs)


class Managers(generics.ListCreateAPIView):
    queryset = Group.objects.get(name='Manager').user_set.all()
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        if request.user.groups.filter(name='Manager').exists():
            username = request.data.get('username')
            if username:
                user = get_object_or_404(User, username=username)
                managers = Group.objects.get(name='Manager')
                managers.user_set.add(user)
                return Response(
                    {'message': f'{username} successfully added to managers group'},
                    status.HTTP_201_CREATED
                )

            return Response(
                {'message': 'username is required'},
                status.HTTP_400_BAD_REQUEST
            )
        return Response({'message':'Not Authorized'}, status=status.HTTP_403_FORBIDDEN)  

        
class ManagerDelete(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, *args, **kwargs):
        if request.user.groups.filter(name='Manager').exists():
            user = get_object_or_404(User, pk=kwargs["pk"])
            managers = Group.objects.get(name='Manager')
            managers.user_set.remove(user)
            return Response(
                {'message': f'{user.username} successfully removed from managers group'},
                status.HTTP_200_OK
            )
        else:
            return Response({'message':'Not Authorized'}, status=status.HTTP_403_FORBIDDEN)

class DeliveryCrews(generics.ListCreateAPIView):
    queryset = Group.objects.get(name='Delivery Crew').user_set.all()
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        if request.user.groups.filter(name='Manager').exists():
            username = request.data.get('username')
            if username:
                user = get_object_or_404(User, username=username)
                delivery_crews = Group.objects.get(name='Delivery Crew')
                delivery_crews.user_set.add(user)
                return Response(
                    {'message': f'{username} successfully added to delivery crews group'},
                    status.HTTP_201_CREATED
                )

            return Response(
                {'message': 'username field is required'},
                status.HTTP_400_BAD_REQUEST
            )
        else:
            return Response({'message':'Not Authorized'}, status=status.HTTP_403_FORBIDDEN)


class DeliveryCrewDelete(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, *args, **kwargs):
        if request.user.groups.filter(name='Manager').exists():
            user = get_object_or_404(User, pk=kwargs["pk"])
            delivery_crews = Group.objects.get(name='Delivery Crew')
            delivery_crews.user_set.remove(user)
            return Response(
                {'message': f'{user.username} successfully removed from delivery crews group'},
                status.HTTP_200_OK
            )
        else:
            return Response({'message':'Not Authorized'}, status=status.HTTP_403_FORBIDDEN)