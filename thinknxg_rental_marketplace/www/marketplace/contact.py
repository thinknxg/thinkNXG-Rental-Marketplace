from thinknxg_rental_marketplace.website import base


def get_context(context):
	return base(context, "Contact", "" or None)
