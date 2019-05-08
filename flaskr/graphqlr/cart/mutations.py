from graphene import List, String, Field, relay, ID, Int
from flaskr.database import CartModel
from flaskr.database import Session as DbSession
from ..mixins import SessionMixin
from .types import ProductCart, PurchaseResult, AddressInput, CreditCardInput
from .helpers import (
    upsert_product_cart,
    resolve_list_product_cart,
    get_cart,
    get_product,
    get_product_cart,
    validate_product_quantity,
    validate_credit_card,
    pay_products_cart,
    decode_id,
)


class CreateCart(relay.ClientIDMutation, SessionMixin):
    confirmation = String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **kwargs):
        cls.create_session()
        DbSession.add(CartModel(id=cls.sid()))
        DbSession.commit()
        return CreateCart(confirmation="success")


class DeleteCart(relay.ClientIDMutation, SessionMixin):
    confirmation = String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **kwargs):
        # print("DELETE PREVIOUS SESSION", session)
        cart = get_cart(cls.sid())
        DbSession.delete(cart)
        DbSession.commit()
        cls.delete_session()
        return DeleteCart(confirmation="success")


class PutProductToCart(relay.ClientIDMutation, SessionMixin):
    class Input:
        id = ID(required=True)
        quantity = Int(required=True)

    payload = List(ProductCart)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **kwargs):
        # sid = str(session["u"])
        cart = get_cart(cls.sid())
        pid = decode_id(str(kwargs.get("id")))
        quantity = kwargs.get("quantity")

        product = get_product(pid)
        validate_product_quantity(product, quantity)

        product_cart = upsert_product_cart(cls.sid(), pid, product, quantity)

        cart.products.append(product_cart)
        DbSession.add(product_cart)
        DbSession.add(cart)
        DbSession.commit()
        cart = (
            DbSession.query(CartModel).filter(CartModel.id == cls.sid()).one()
        )
        return PutProductToCart(
            payload=resolve_list_product_cart(cart.products)
        )


class RemoveProductOfCart(relay.ClientIDMutation, SessionMixin):
    class Input:
        id = ID(required=True)

    payload = List(ProductCart)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **kwargs):
        pid = decode_id(kwargs.get("id"))
        cart = get_cart(cls.sid())

        product_cart = get_product_cart(cls.sid(), pid)
        DbSession.delete(product_cart)
        DbSession.commit()
        return RemoveProductOfCart(
            payload=resolve_list_product_cart(cart.products)
        )


class PayCart(relay.ClientIDMutation, SessionMixin):
    class Input:
        full_name = String(required=True)
        address = AddressInput(required=True)
        credit_card = CreditCardInput(required=True)

    payload = Field(PurchaseResult)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **kwargs):
        # read params
        fullname = kwargs.get("full_name")
        creditcard_in = kwargs.get("credit_card")
        address_in = kwargs.get("address")
        card_number = creditcard_in["card_number"]

        # read cart if exists
        cart = get_cart(cls.sid())

        validate_credit_card(card_number)

        products_paid = resolve_list_product_cart(cart.products)

        total_paid = pay_products_cart(cls.sid())

        return PayCart(
            payload=PurchaseResult(
                customer=fullname,
                address=address_in,
                total_paid=total_paid,
                products_paid=products_paid,
            )
        )
