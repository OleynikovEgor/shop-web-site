import json
from flask import Blueprint, jsonify, request
from .db_session import create_session
from .products import Product, ProductVariant
from .reviews import Review

api = Blueprint('api', __name__, url_prefix='/api')


@api.route('/variant/<int:variant_id>', methods=['GET'])
def get_variant(variant_id):
    sess = create_session()
    variant = sess.get(ProductVariant, variant_id)
    if not variant:
        return jsonify({'error': 'Variant not found'}), 404

    return jsonify({
        'id': variant.id,
        'name': variant.name,
        'type': variant.type,
        'price': variant.price,
        'stock': variant.stock,
        'rating': variant.rating,
        'reviews_count': variant.reviews_cnt
    })


@api.route('/variant/<int:variant_id>/reviews', methods=['GET'])
def get_variant_reviews(variant_id):
    sess = create_session()
    variant = sess.get(ProductVariant, variant_id)
    if not variant:
        return jsonify({'error': 'Variant not found'}), 404

    data = []
    for r in variant.reviews:
        data.append({
            'id': r.id,
            'user_id': r.user_id,
            'rating': r.rating,
            'text': r.text,
            'images': json.loads(r.images or '[]'),
            'video_url': r.video_url,
            'created_at': r.created_at.isoformat()
        })
    return jsonify(data)


@api.route('/products', methods=['GET'])
def search_variants():
    q = request.args.get('q', '').strip()
    sess = create_session()
    query = sess.query(ProductVariant)
    if q:
        query = query.filter(ProductVariant.name.ilike(f'%{q}%'))
    variants = query.all()

    return jsonify([
        {
            'id': v.id,
            'name': v.name,
            'type': v.type,
            'price': v.price,
            'stock': v.stock,
            'rating': v.rating,
            'reviews_count': v.reviews_cnt
        }
        for v in variants
    ])


@api.route('/product/<int:product_id>', methods=['GET'])
def get_product(product_id):
    sess = create_session()
    prod = sess.get(Product, product_id)
    if not prod:
        return jsonify({'error': 'Product not found'}), 404

    return jsonify({
        'id': prod.id,
        'variants': [
            {
                'id': v.id,
                'name': v.name,
                'type': v.type,
                'price': v.price,
                'stock': v.stock,
                'rating': v.rating,
                'reviews_count': v.reviews_cnt
            } for v in prod.variants
        ]
    })
