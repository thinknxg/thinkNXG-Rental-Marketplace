"""Generate Frappe DocType JSON (+ controller stubs) from tools/doctype_spec.py.

Usage: python3 tools/gen_doctypes.py          (idempotent; never overwrites a hand-written controller)
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from doctype_spec import DOCTYPES, perms  # noqa: E402

APP = "thinknxg_rental_marketplace"
MODULE = "Rental Marketplace"
ROOT = os.path.join(os.path.dirname(HERE), APP, "rental_marketplace", "doctype")
STAMP = "2026-11-15 10:00:00.000000"


def scrub(name):
	return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def label_of(fieldname):
	words = fieldname.replace("_", " ").split()
	special = {"id": "ID", "erp": "ERP", "uom": "UOM", "url": "URL", "iban": "IBAN", "vat": "VAT", "km": "(km)", "kg": "(kg)"}
	return " ".join(special.get(w, w.capitalize() if i == 0 else w) for i, w in enumerate(words))


def parse_field(spec, counter):
	parts = spec.split("|")
	if parts[0] == "--":
		counter[0] += 1
		f = {"fieldname": f"section_{counter[0]}", "fieldtype": "Section Break", "label": parts[1] if len(parts) > 1 else ""}
		if len(parts) > 2 and parts[2].startswith("dep="):
			f["depends_on"] = parts[2][4:].replace("~", " ")
		return f
	if spec == "||":
		counter[0] += 1
		return {"fieldname": f"column_{counter[0]}", "fieldtype": "Column Break"}
	fieldname, ftype = parts[0], parts[1]
	options = parts[2] if len(parts) > 2 else ""
	flags = parts[3].split() if len(parts) > 3 else []
	f = {"fieldname": fieldname, "fieldtype": ftype, "label": label_of(fieldname)}
	if options:
		f["options"] = "\n".join(options.split(";")) if ftype == "Select" else options
		if ftype == "Select" and options.startswith(";"):
			f["options"] = "\n" + "\n".join(options[1:].split(";"))
	simple = {"r": "reqd", "ro": "read_only", "l": "in_list_view", "sf": "in_standard_filter", "u": "unique",
		"i": "search_index", "h": "hidden", "nc": "no_copy", "b": "bold", "gl": "in_global_search", "coll": "collapsible"}
	for flag in flags:
		if flag in simple:
			f[simple[flag]] = 1
		elif flag == "p1":
			f["permlevel"] = 1
		elif "=" in flag:
			k, v = flag.split("=", 1)
			if k == "d":
				f["default"] = v.replace("_", " ") if ftype not in ("Link",) else v
			elif k == "dep":
				f["depends_on"] = v.replace("~", " ")
			elif k == "lbl":
				f["label"] = v.replace("_", " ")
			elif k == "ff":
				f["fetch_from"] = v
			elif k == "desc":
				f["description"] = v.replace("_", " ")
			elif k == "prec":
				f["precision"] = v
	if ftype in ("Currency",) and options and options != "currency":
		pass
	if f.get("unique") and ftype == "Data" and fieldname in ("idempotency_key", "route"):
		f["no_copy"] = 1
	return f


def build(name, d):
	counter = [0]
	fields = [parse_field(s, counter) for s in d["fields"]]
	if d["tree"]:
		for fdef in fields:
			if fdef["fieldname"] == "lft":
				fdef.update(label="Left", fieldname="lft")
			if fdef["fieldname"] == "rgt":
				fdef.update(label="Right")
	doc = {
		"actions": [], "allow_rename": 0, "creation": STAMP, "modified": STAMP, "doctype": "DocType",
		"engine": "InnoDB", "field_order": [f["fieldname"] for f in fields], "fields": fields,
		"index_web_pages_for_search": 0, "links": [], "module": MODULE, "name": name, "owner": "Administrator",
		"modified_by": "Administrator", "naming_rule": "", "sort_field": d["sort"], "sort_order": "DESC",
		"states": [], "description": d["desc"],
	}
	if d["istable"]:
		doc.update(istable=1, editable_grid=1, permissions=[])
	else:
		doc["permissions"] = perms(d["kind"])
	if d["single"]:
		doc["issingle"] = 1
	if d["autoname"]:
		doc["autoname"] = d["autoname"]
		if d["autoname"].startswith("field:"):
			doc["naming_rule"] = "By fieldname"
		elif d["autoname"] == "hash":
			doc["naming_rule"] = "Random"
		else:
			doc["naming_rule"] = "Expression (old style)"
	if d["title"]:
		doc["title_field"] = d["title"]
		doc["show_title_field_in_link"] = 1
	if d["search"]:
		doc["search_fields"] = d["search"]
	if d["track"]:
		doc["track_changes"] = 1
	if d["tree"]:
		doc["is_tree"] = 1
		doc["nsm_parent_field"] = "parent_marketplace_category"
	if d["image"]:
		doc["image_field"] = d["image"]
	return doc


CONTROLLER = '''# Copyright (c) 2026, thinkNXG and contributors
# License: MIT. See license.txt

{imports}


class {cls}({base}):
	pass
'''


def main():
	os.makedirs(ROOT, exist_ok=True)
	open(os.path.join(ROOT, "__init__.py"), "a").close()
	names = []
	for name, d in DOCTYPES.items():
		folder = os.path.join(ROOT, scrub(name))
		os.makedirs(folder, exist_ok=True)
		open(os.path.join(folder, "__init__.py"), "a").close()
		with open(os.path.join(folder, scrub(name) + ".json"), "w") as fh:
			json.dump(build(name, d), fh, indent=1, sort_keys=True)
			fh.write("\n")
		ctrl = os.path.join(folder, scrub(name) + ".py")
		if not os.path.exists(ctrl):
			if d["tree"]:
				imports, base = "from frappe.utils.nestedset import NestedSet", "NestedSet"
			else:
				imports, base = "from frappe.model.document import Document", "Document"
			with open(ctrl, "w") as fh:
				fh.write(CONTROLLER.format(imports=imports, cls=name.replace(" ", "").replace("-", ""), base=base))
		names.append(name)
	print(f"{len(names)} DocTypes generated in {ROOT}")


if __name__ == "__main__":
	main()
