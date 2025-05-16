import json
from datetime import datetime, timezone
from data import db_session
from data.reviews import Review
from data.products import ProductVariant

def main():

    db_session.global_init("db/Buyers.db")
    sess = db_session.create_session()


    user_id     = 1
    variant_id  = 2
    text        = "Потрясающие часы! Отличное качество."
    rating      = 5
    images_list = []
    video_url   = "video_test.mp4"

    review = Review(
        user_id    = user_id,
        variant_id = variant_id,
        text       = text,
        rating     = rating,
        images     = json.dumps(images_list),
        video_url  = video_url,
        created_at = datetime.now(timezone.utc)
    )
    sess.add(review)
    sess.flush()

    variant = sess.get(ProductVariant, variant_id)
    cnt = len(variant.reviews)
    total = sum(r.rating for r in variant.reviews)

    variant.reviews_cnt = cnt
    variant.rating      = total / cnt if cnt else 0.0

    sess.commit()

    print(f"Отзыв #{review.id} добавлен к variant {variant_id}. "
          f"Теперь reviews_cnt={cnt}, rating={variant.rating:.2f}")

if __name__ == "__main__":
    main()
