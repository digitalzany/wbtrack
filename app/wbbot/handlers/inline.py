import json

from sqlalchemy import and_

from common.di_container import product_service
from common.di_container import user_service
from common.models import *
from wbbot.misc.catalog import get_catalog, get_catalog_markup
from wbbot.misc.product_card import get_product_card, get_price_icon, get_product_markup


def inline_callback(update, context):
    callback_data = json.loads(update.callback_query.data)
    globals()['action_' + callback_data['action']](update.callback_query, callback_data)


def action_delete_product(query, data):
    user = user_service.get_user(query.from_user.id)
    product_id = data['product_id']

    product = product_service.get_product_by_id(product_id)

    if product_service.is_user_product_exist(user.id, product.id):
        product_service.delete_user_product(user.id, product.id)
    else:
        return query.message.reply_text('❗ Товар не найден')

    return query.message.reply_html(f'❌ Товар {product.header} удален из списка')


def action_prices_history(query, data):
    user = user_service.get_user(query.from_user.id)

    product = product_service.get_product_by_id(data['product_id'])
    product_prices = product.prices[:30]

    text = f'📈 Цены на {product.header}\n\n'

    if not product_prices:
        text += 'нет данных'

    for product_price in product_prices:
        price_icon = get_price_icon(product_price.value, product_price.prev_value)
        price_value = ProductPrice.format_price_value(product_price.value, product.domain)

        text += f'{product_price.created_at.date()}  {price_icon} {price_value}\n'

    return query.message.reply_html(text, reply_markup=get_product_markup(user.id, product))


def action_brand_list(query, data):
    user = user_service.get_user(query.from_user.id)
    brand_id = data['brand_id']

    products = product_service.session.query(Product).filter(and_(
        Product.id.in_([user_product.product_id for user_product in user.user_products]), Product.brand_id == brand_id)
    )

    for product in products:
        query.message.reply_html(get_product_card(product), reply_markup=get_product_markup(user.id, product))


def action_price_notify(query, data):
    user = user_service.get_user(query.from_user.id)
    user_product = product_service.get_user_product(user.id, data['product_id'])

    if not user_product:
        return

    user_product.settings.is_price_notify = not data['n']
    product_service.session.commit()

    if user_product.settings.is_price_notify:
        text = f'🔔 Включены уведомления для {user_product.product.header}'
    else:
        text = f'🔕 Отключены уведомления для {user_product.product.header}'

    return query.message.reply_html(text, reply_markup=get_product_markup(user.id, product=user_product.product))


def action_catalog_category(query, data):
    user = user_service.get_user(query.from_user.id)
    category_id = data['id']

    if category_id is None:
        product_ids = product_service.session.query(UserProduct.product_id).filter_by(user_id=user.id).distinct()
        products = product_service.session.query(Product).filter(Product.id.in_(product_ids),
                                                                 Product.catalog_category_ids == '{}')

        for product in products:
            query.message.reply_html(get_product_card(product),
                                     reply_markup=get_product_markup(user.id, product))

    else:
        rows = get_catalog(product_service.session, user.id, data['level'], category_id)

        if len(rows) < 2:
            product_ids = product_service.session.query(UserProduct.product_id).filter_by(user_id=user.id).distinct()
            products = product_service.session.query(Product).filter(Product.id.in_(product_ids),
                                                                     Product.catalog_category_ids.any(category_id))
            for product in products:
                query.message.reply_html(get_product_card(product),
                                         reply_markup=get_product_markup(user.id, product))

        else:
            return query.message.reply_html('🗂️ Категории:', reply_markup=get_catalog_markup(rows))
