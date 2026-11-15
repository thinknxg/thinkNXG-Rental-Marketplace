from thinknxg_rental_marketplace.website import base


def get_context(context):
	base(context, "Equipment Categories", "categories")
	context.groups = [{**g, "children": [c for c in context.mp_categories if c.parent == g.name]} for g in context.mp_top_categories]
	return context
