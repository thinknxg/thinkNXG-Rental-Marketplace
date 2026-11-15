from thinknxg_rental_marketplace.website import base


def get_context(context):
	return base(context, "Terms of Use", "" or None)
