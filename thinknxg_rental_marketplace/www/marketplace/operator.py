from thinknxg_rental_marketplace.website import portal


def get_context(context):
	return portal(context, "operator", "Operator console")
