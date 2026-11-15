from thinknxg_rental_marketplace.website import base


def get_context(context):
	return base(context, "Create a Customer Account", "" or None)
