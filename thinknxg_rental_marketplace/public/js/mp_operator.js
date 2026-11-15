/* Operator console: onboarding, moderation, matching overrides, evaluation, finance, trust & analytics. */
(function () {
	const h = MP.h, esc = MP.esc, O = (m, a) => MP.call("operator." + m, a), BASE = "/marketplace/operator";
	const nav = [["Overview"], ["", "chart", "Analytics", "^$"], ["Supply & demand"], ["vendors", "shield", "Suppliers", "^vendors"], ["customers", "users", "Customers", "^customers"], ["listings", "layers", "Listings", "^listings"],
		["Tenders"], ["tenders", "gavel", "Tenders & matching", "^tenders"], ["bookings", "truck", "Bookings", "^bookings"],
		["Finance"], ["payments", "card", "Payments & refunds", "^payments"], ["commissions", "money", "Commissions", "^commissions"], ["settlements", "scale", "Settlements", "^settlements"], ["subscriptions", "tag", "Subscriptions", "^subscriptions"],
		["Trust"], ["reviews", "star", "Reviews", "^reviews"], ["disputes", "alert", "Disputes", "^disputes"], ["enquiries", "doc", "Enquiries", "^enquiries"], ["audit", "list", "Audit trail", "^audit"], ["settings", "cog", "Configuration", "^settings"]];
	MP.$("#side-nav").innerHTML = nav.map((n) => (n.length === 1 ? `<div class="sec">${n[0]}</div>` : `<a href="${BASE}/${n[0]}" data-match="${n[3]}">${MP.icon(n[1])}${n[2]}</a>`)).join("");
	MP.$(".bell").onclick = () => MP.notifPanel("operator");
	const actions = (...els) => { const b = MP.$("#bar-actions"); b.innerHTML = ""; els.filter(Boolean).forEach((e) => b.append(e)); };
	const tabsFor = (path, cur, list) => h("div", { class: "tabs" }, list.map(([k, l]) => h("a", { href: `${BASE}/${path}${k ? "?status=" + encodeURIComponent(k) : ""}`, class: k === cur ? "on" : "" }, l)));
	const btn = (label, fn, cls = "btn sm") => h("button", { class: cls, onclick: fn }, label);
	const act = async (fn, msg) => { await MP.safe(fn, msg); MP.reload(); };
	const history = (rows) => h("div", { class: "timeline" }, rows.map((e) => h("div", {}, h("b", {}, e.event), e.from_state || e.to_state ? ` ${e.from_state || ""} → ${e.to_state || ""}` : "", h("span", { class: "muted" }, ` · ${e.actor} · ${MP.dt(e.creation)}`))));

	async function analytics() {
		const d = await O("dashboard"), c = d.counts, r = d.revenue; MP.setBell(d.notifications.unread); actions();
		const money = (v) => MP.money(v);
		return { title: "Marketplace analytics", el: h("div", { class: "stack" },
			MP.kpis([{ label: "Total requests", value: c.requests_total }, { label: "Active tenders", value: c.tenders_active, href: BASE + "/tenders" }, { label: "Offers (30 days)", value: c.offers_30d }, { label: "Request → booking conversion", value: d.conversion + "%" }]),
			MP.kpis([{ label: "Active suppliers", value: c.vendors_active, href: BASE + "/vendors?status=Approved" }, { label: "Avg suppliers invited / tender", value: d.avg_suppliers_per_tender }, { label: "Avg offers / tender", value: d.avg_offers_per_tender }, { label: "Active bookings", value: c.bookings_active, href: BASE + "/bookings" }]),
			h("div", { class: "grid g4" }, [["Supplier applications", c.vendors_pending, "vendors?status=Submitted,Documents Pending,Under Review"], ["Tenders to moderate", c.tenders_moderation, "tenders?status=Submitted,Suspended"], ["Payments to confirm", c.payments_to_confirm, "payments?status=Pending"],
				["Open disputes", c.disputes_open, "disputes"], ["Reviews to moderate", c.reviews_pending, "reviews"], ["Customers", c.customers, "customers"]].map(([k, v, p]) => h("a", { class: "card kpi", href: `${BASE}/${p}`, style: v ? { borderColor: "#f3d18f", background: "var(--amber-soft)" } : null }, h("span", {}, k), h("b", {}, v)))),
			h("div", { class: "grid g2" },
				h("div", { class: "card" }, h("h3", {}, "Marketplace revenue"), h("dl", { class: "dl" }, h("dt", {}, "Commission earned"), h("dd", {}, money(r.commission_earned)), h("dt", {}, "Commission accrued (in progress)"), h("dd", {}, money(r.commission_accrued)),
					h("dt", {}, "Subscriptions"), h("dd", {}, money(r.subscriptions)), h("dt", {}, "Promotions & listing fees"), h("dd", {}, money(r.promotions)))),
				h("div", { class: "card" }, h("h3", {}, "Booking value by transaction type"), MP.table([{ label: "Type", key: "transaction_type" }, { label: "Bookings", key: "n", right: 1 }, { label: "Value", html: (x) => money(x.value), right: 1 }, { label: "Commission", html: (x) => money(x.commission), right: 1 }], d.by_transaction))),
			h("div", { class: "grid g2" },
				h("div", { class: "card" }, h("h3", {}, "Category performance"), MP.table([{ label: "Category", key: "category" }, { label: "Tenders", key: "tenders", right: 1 }, { label: "Bookings", key: "bookings", right: 1 }, { label: "Value", html: (x) => money(x.value), right: 1 }], d.by_category)),
				h("div", { class: "card" }, h("h3", {}, "Geographic performance"), MP.table([{ label: "Country", key: "country" }, { label: "Tenders", key: "tenders", right: 1 }, { label: "Bookings", key: "bookings", right: 1 }, { label: "Value", html: (x) => money(x.value), right: 1 }], d.by_country)))) };
	}

	// ---------------------------------------------------------------- suppliers & customers
	async function vendors(p, q) {
		const status = q.get("status") || "Submitted,Documents Pending,Under Review";
		const res = await O("vendors_list", { status, q: q.get("q") || "" }); actions();
		return { title: "Suppliers", el: h("div", {}, tabsFor("vendors", status, [["Submitted,Documents Pending,Under Review", "Applications"], ["Approved", "Approved"], ["Suspended", "Suspended"], ["Rejected", "Rejected"], ["Draft", "Drafts"], ["", "All"]]),
			MP.table([{ label: "Supplier", html: (v) => `<b>${esc(v.business_name)}</b><div class="small muted">${esc(v.business_type)} · ${esc(v.city)}, ${esc(v.country)}</div>` }, { label: "Status", html: (v) => MP.badge(v.status) + (v.verified ? ' <span class="badge green">✔</span>' : "") },
				{ label: "Performance", html: (v) => `${v.review_count ? MP.stars(v.rating) + " " + v.rating : "—"}<div class="tiny muted">${v.offers_won || 0} won / ${v.offers_submitted || 0} offers</div>` }, { label: "ERP", html: (v) => esc(v.erp_company || "—") }, { label: "Submitted", html: (v) => MP.date(v.submitted_on) }],
				res.rows, { onclick: (v) => MP.go(`${BASE}/vendors/${encodeURIComponent(v.name)}`) })) };
	}
	async function vendor({ name }) {
		const v = await O("vendor_get", { name });
		const setStatus = async (s) => { const r = ["Rejected", "Suspended", "Deactivated", "Documents Pending"].includes(s) ? await MP.prompt(`${s}: ${v.business_name}`, [{ name: "reason", label: "Reason (sent to the supplier)", full: 1, reqd: 1 }], s) : (await MP.confirm(`${s}?`, `Set ${v.business_name} to ${s}.`, s)) && {};
			if (r) act(() => O("vendor_set_status", { name, status: s, reason: r.reason }), "Status updated"); };
		actions(...v.transitions.map((s) => btn(s === "Approved" ? "Approve" : s, () => setStatus(s), "btn sm " + (s === "Approved" ? "green" : ["Rejected", "Suspended", "Deactivated"].includes(s) ? "ghost" : ""))));
		return { title: v.business_name, el: h("div", { class: "stack" },
			h("div", { class: "card row between" }, h("div", {}, h("h2", { style: { margin: 0 } }, v.business_name), h("span", { class: "muted" }, `${v.name} · ${v.business_type}`)), h("span", { html: MP.badge(v.status) + (v.verified ? ' <span class="badge green">Verified</span>' : "") })),
			h("div", { class: "grid g2" }, h("div", { class: "card" }, h("h3", {}, "Registration"), h("dl", { class: "dl" }, ...[["Registration no.", v.registration_number], ["Tax / VAT", v.tax_id], ["Address", [v.address_line1, v.address_line2, v.city, v.state, v.country].filter(Boolean).join(", ")],
				["Contact", `${v.contact_person} · ${v.email} · ${v.phone}`], ["Website", v.website], ["Categories", (v.categories || []).map((c) => c.category).join(", ")], ["Locations", (v.locations || []).map((l) => `${l.city} (${l.delivery_radius_km || "-"} km)`).join(", ")],
				["Listings", v.listings], ["Bank", v.iban ? `${v.bank_name || ""} · ${v.iban}` : "Hidden / not set"]].flatMap(([k, x]) => [h("dt", {}, k), h("dd", {}, x || "—")]))),
				h("div", { class: "card" }, h("h3", {}, "ERP connection"), h("p", { class: "small muted" }, "Set an ERP company to fulfil this supplier's bookings through thinkNXG Rental / ERPNext on this site."),
					MP.formFields([{ name: "erp_company", label: "ERP Company", value: v.erp_company }, { name: "erp_supplier", label: "ERP Supplier", value: v.erp_supplier }]), btn("Save ERP link", (e) => act(() => O("vendor_erp_link", { name, ...MP.readForm(e.target.closest(".card")) }), "Saved"), "btn ghost sm"),
					h("h3", { style: { marginTop: "18px" } }, "Subscriptions"), MP.table([{ label: "Plan", key: "plan" }, { label: "Status", html: (s) => MP.badge(s.status) }, { label: "Ends", html: (s) => MP.date(s.end_date) }], v.subscriptions))),
			h("div", { class: "card" }, h("h3", {}, "Verification documents"), MP.table([{ label: "Document", html: (d) => `<a href="${MP.fileLink(d.attachment)}" target="_blank">📎 ${esc(d.document_type)}</a>` }, { label: "Number", key: "document_number" }, { label: "Expiry", html: (d) => MP.date(d.expiry_date) },
				{ label: "Status", html: (d) => MP.badge(d.status) }, { label: "", html: (d) => `<button class="btn sm" data-doc="${esc(d.name)}" data-s="Approved">Approve</button> <button class="btn ghost sm" data-doc="${esc(d.name)}" data-s="Rejected">Reject</button>` }], v.documents, { empty: "No documents uploaded." })),
			h("div", { class: "card" }, h("h3", {}, "Users"), MP.table([{ label: "User", key: "user" }, { label: "Role", key: "vendor_role" }, { label: "Enabled", html: (u) => (u.enabled ? "Yes" : "No") }], v.users)),
			h("div", { class: "card" }, h("h3", {}, "History"), history(v.history))) };
	}
	document.addEventListener("click", async (e) => { const b = e.target.closest("[data-doc]"); if (b) { const r = b.dataset.s === "Rejected" ? await MP.prompt("Reject document", [{ name: "remarks", label: "Reason", full: 1, reqd: 1 }], "Reject") : {}; if (r) act(() => O("vendor_document_review", { name: b.dataset.doc, status: b.dataset.s, remarks: r.remarks }), "Document " + b.dataset.s.toLowerCase()); } });
	async function customers(p, q) {
		const status = q.get("status") || ""; const res = await O("customers_list", { status, q: q.get("q") || "" }); actions();
		return { title: "Customers", el: h("div", {}, tabsFor("customers", status, [["", "All"], ["Active", "Active"], ["Restricted", "Restricted"], ["Suspended", "Suspended"]]),
			MP.table([{ label: "Customer", html: (c) => `<b>${esc(c.customer_name)}</b><div class="small muted">${esc(c.email)} · ${esc(c.city || "")} ${esc(c.country || "")}</div>` }, { label: "Type", key: "customer_type" },
				{ label: "Status", html: (c) => MP.badge(c.status) + (c.verified ? ' <span class="badge green">Verified</span>' : "") }, { label: "Since", html: (c) => MP.date(c.creation) },
				{ label: "", html: (c) => `<button class="btn ghost sm" data-cust="${esc(c.name)}">Manage</button>` }], res.rows)) };
	}
	document.addEventListener("click", async (e) => { const b = e.target.closest("[data-cust]"); if (!b) return;
		const v = await MP.prompt("Manage customer account", [{ name: "status", label: "Status", type: "select", options: ["Active", "Restricted", "Suspended"] }, { name: "verified", label: "Company verified", type: "check" }, { name: "reason", label: "Reason", full: 1 }], "Save");
		if (v) act(() => O("customer_set_status", { name: b.dataset.cust, ...v }), "Updated"); });

	// ---------------------------------------------------------------- tenders
	async function tenders(p, q) {
		const status = q.get("status") || "";
		const res = await O("tenders_list", { status, q: q.get("q") || "" }); actions();
		return { title: "Tenders & matching", el: h("div", {}, tabsFor("tenders", status, [["", "All"], ["Submitted,Suspended", "Moderation"], ["Bidding Open", "Bidding open"], ["Bidding Closed,Evaluation", "Evaluation"], ["Awarded", "Awarded"], ["Cancelled,Expired", "Closed"]]),
			MP.table([{ label: "Tender", html: (t) => `<b>${esc(t.title)}</b><div class="small muted">${esc(t.name)} · ${esc(t.category)} · ${esc(t.city || "")} ${esc(t.country || "")}</div>` }, { label: "Type", html: (t) => `${esc(t.transaction_type)}<div class="tiny muted">${esc(t.tender_type)} · ${esc(t.visibility)}</div>` },
				{ label: "Status", html: (t) => MP.badge(t.status) }, { label: "Deadline", html: (t) => MP.dt(t.submission_deadline) }, { label: "Invited / offers", html: (t) => `${t.invited_count} / ${t.offers_count}`, right: 1 }], res.rows,
				{ onclick: (t) => MP.go(`${BASE}/tenders/${encodeURIComponent(t.name)}`) })) };
	}
	async function tender({ name }) {
		const t = await O("tender_get", { name }), cur = t.currency;
		const run = (action, data, msg) => act(() => O("tender_action", { name, action, data }), msg);
		const ask = async (label, fields, action, msg) => { const v = await MP.prompt(label, fields, label); if (v) { if (v.deadline) v.deadline = v.deadline.replace("T", " ") + ":00"; run(action, v, msg); } };
		actions(["Submitted", "Suspended"].includes(t.status) && !t.published_on ? btn("Publish & match", () => run("publish", {}, "Published — suppliers invited"), "btn green sm") : null,
			t.status === "Suspended" && t.published_on ? btn("Resume", () => run("resume", {}, "Resumed")) : null,
			!["Awarded", "Cancelled", "Suspended", "Expired"].includes(t.status) ? btn("Suspend", () => ask("Suspend tender", [{ name: "reason", label: "Reason", full: 1, reqd: 1 }], "suspend", "Suspended"), "btn ghost sm") : null,
			!["Awarded", "Cancelled"].includes(t.status) ? btn("Extend", () => ask("Extend deadline", [{ name: "deadline", label: "New deadline", type: "datetime-local", reqd: 1 }, { name: "reason", label: "Reason", full: 1 }], "extend", "Extended"), "btn ghost sm") : null,
			t.status === "Bidding Open" ? btn("Close bidding now", async () => (await MP.confirm("Close bidding?", "Offers open to the customer immediately.", "Close")) && run("close", {}, "Bidding closed"), "btn ghost sm") : null,
			!["Awarded", "Cancelled"].includes(t.status) ? btn("Cancel", () => ask("Cancel tender", [{ name: "reason", label: "Reason (sent to customer and suppliers)", full: 1, reqd: 1 }], "cancel", "Cancelled"), "btn ghost sm") : null);
		const rules = MP.formFields([{ name: "tender_type", label: "Tender type", type: "select", options: ["Open", "Invited", "Restricted", "Private", "Negotiated", "Reverse Auction"], value: t.tender_type },
			{ name: "visibility", label: "Visibility", type: "select", options: ["Public Marketplace", "Verified Suppliers", "Category Restricted", "Location Restricted", "Selected Suppliers"], value: t.visibility },
			{ name: "confidentiality", label: "Bid confidentiality", type: "select", options: ["Sealed", "Rank Only", "Open"], value: t.confidentiality }, { name: "disclosure_stage", label: "Disclose customer", type: "select", options: ["On Award", "On Shortlist", "Always"], value: t.disclosure_stage },
			{ name: "evaluation_method", label: "Evaluation", type: "select", options: ["Customer Choice", "Lowest Price", "Weighted Score"], value: t.evaluation_method }, { name: "max_revisions", label: "Max revisions", type: "number", value: t.max_revisions },
			{ name: "min_vendor_rating", label: "Min supplier rating", type: "number", value: t.min_vendor_rating }, { name: "reserve_price", label: "Reverse auction ceiling", type: "number", value: t.reserve_price },
			{ name: "require_verified", label: "Verified suppliers only", type: "check", value: t.require_verified }, { name: "allow_revisions", label: "Allow revisions", type: "check", value: t.allow_revisions }, { name: "allow_alternatives", label: "Allow alternatives", type: "check", value: t.allow_alternatives },
			{ name: "show_budget", label: "Show budget to suppliers", type: "check", value: t.show_budget }, { name: "featured", label: "Featured tender", type: "check", value: t.featured },
			{ name: "required_qualifications", label: "Required qualifications", type: "textarea", value: t.required_qualifications }, { name: "terms", label: "Terms & conditions", type: "textarea", value: t.terms }], "grid g3");
		const candBox = h("div", {}, btn("Preview automated matching", async (e) => { e.target.disabled = true; const rows = await MP.safe(() => O("tender_candidates", { name }));
			candBox.innerHTML = ""; candBox.append(MP.table([{ label: "", html: (r) => (r.invited ? "✔" : `<input type="checkbox" value="${esc(r.vendor)}">`) }, { label: "Supplier", key: "vendor_name" }, { label: "Score", html: (r) => `<b>${r.score}</b>`, right: 1 }, { label: "Free qty", html: (r) => MP.num(r.free_qty), right: 1 }, { label: "Why", html: (r) => esc(r.reasons.join(" · ")) }], rows, { empty: "No eligible suppliers — check categories, coverage and subscriptions." }),
				rows.length ? btn("Invite selected", () => { const vs = MP.$$("input[type=checkbox]:checked", candBox).map((x) => x.value); if (vs.length) run("invite", { vendors: vs }, `${vs.length} supplier(s) invited`); }, "btn sm") : ""); }, "btn ghost sm"));
		const manual = h("form", { class: "row", onsubmit: (e) => { e.preventDefault(); const v = e.target.vendor.value.trim(); if (v) run("invite", { vendors: [v] }, "Invited (admin override)"); } }, h("input", { name: "vendor", placeholder: "Supplier ID (VND-…) to invite manually", style: { flex: 1 } }), h("button", { class: "btn ghost sm" }, "Invite"));
		return { title: t.name, el: h("div", { class: "stack" },
			h("div", { class: "card row between" }, h("div", {}, h("span", { class: "eyebrow" }, `${t.transaction_type} · ${t.category}`), h("h2", { style: { margin: "4px 0" } }, t.title), h("span", { class: "muted" }, `Customer ${t.customer_name} · request ${t.rental_request} · ${t.city || ""} ${t.country || ""}`)),
				h("div", { class: "stack right" }, h("span", { html: MP.badge(t.status) }), h("span", { class: "small" }, "Deadline " + MP.dt(t.submission_deadline)), t.booking ? h("a", { href: `${BASE}/bookings/${t.booking}` }, "Booking " + t.booking) : "")),
			h("div", { class: "card" }, h("h3", {}, "Requirement"), MP.table([{ label: "Item", key: "equipment_name" }, { label: "Qty", html: (i) => esc(i.qty + " " + i.uom), right: 1 }, { label: "Specs", key: "specifications" }], t.items)),
			h("div", { class: "card" }, h("div", { class: "row between" }, h("h3", {}, "Tender rules"), btn("Save rules", () => run("settings", MP.readForm(rules), "Rules saved"), "btn ghost sm")), rules),
			h("div", { class: "card" }, h("h3", {}, `Invitations (${t.invitations.length})`), MP.table([{ label: "Supplier", html: (i) => `<a href="${BASE}/vendors/${esc(i.vendor)}">${esc(i.vendor_name)}</a>` }, { label: "Source", key: "source" }, { label: "Score", key: "match_score", right: 1 },
				{ label: "Why", key: "match_reasons" }, { label: "Status", html: (i) => MP.badge(i.status) }, { label: "", html: (i) => (i.status !== "Excluded" ? `<button class="btn ghost sm" data-excl="${esc(i.name)}">Exclude</button>` : "") }], t.invitations),
				h("h4", { style: { marginTop: "16px" } }, "Matching override"), candBox, manual),
			h("div", { class: "card" }, h("h3", {}, `Offers (${t.offers.length}) — operator view`), MP.table([{ label: "Supplier", key: "vendor_name" }, { label: "Status", html: (o) => MP.badge(o.status) + (o.shortlisted ? " ★" : "") }, { label: "Total", html: (o) => MP.money(o.grand_total, cur), right: 1 },
				{ label: "Delivery", html: (o) => MP.date(o.delivery_date) }, { label: "Compliance", key: "technical_compliance" }, { label: "Revisions", html: (o) => o.revisions.map((r) => `<a href="#" data-rev="${esc(r.name)}">r${r.revision_no}: ${MP.money(r.grand_total, cur)}</a>`).join("<br>") },
				{ label: "Evaluate", html: (o) => `<button class="btn ghost sm" data-eval="${esc(o.name)}">Evaluate</button>` }], t.offers, { empty: "No offers yet." })),
			t.clarifications.length ? h("div", { class: "card" }, h("h3", {}, "Clarifications & negotiation"), MP.table([{ label: "Subject", key: "subject" }, { label: "Party", key: "raised_by_party" }, { label: "Type", key: "clarification_type" }, { label: "Status", html: (c) => MP.badge(c.status) }, { label: "Response", key: "response" }], t.clarifications)) : "",
			h("div", { class: "card" }, h("h3", {}, "Audit history"), history(t.history))) };
	}
	document.addEventListener("click", async (e) => {
		const ex = e.target.closest("[data-excl]"), ev = e.target.closest("[data-eval]"), rv = e.target.closest("[data-rev]");
		const tname = location.pathname.split("/tenders/")[1];
		if (ex && (await MP.confirm("Exclude supplier?", "They lose access to this tender.", "Exclude"))) act(() => O("tender_action", { name: decodeURIComponent(tname), action: "exclude", data: { invitation: ex.dataset.excl } }), "Excluded");
		if (ev) { const v = await MP.prompt("Technical & commercial evaluation", [{ name: "technical_result", label: "Technical", type: "select", options: ["Pending", "Accepted", "Rejected"] }, { name: "commercial_result", label: "Commercial", type: "select", options: ["Pending", "Accepted", "Rejected"] },
			{ name: "manual_score", label: "Manual / technical score (0-100)", type: "number" }, { name: "remarks", label: "Remarks", type: "textarea", full: 1 }], "Record evaluation"); if (v) act(() => O("offer_evaluate", { offer: ev.dataset.eval, ...v }), "Evaluation recorded"); }
		if (rv) { e.preventDefault(); const r = await MP.safe(() => O("offer_revision", { name: rv.dataset.rev })); MP.modal({ title: `Revision ${r.revision_no} · ${r.offer}`, wide: true, body: h("pre", { style: { whiteSpace: "pre-wrap", fontSize: ".78rem", maxHeight: "60vh", overflow: "auto" } }, JSON.stringify(typeof r.snapshot === "string" ? JSON.parse(r.snapshot) : r.snapshot, null, 2)) }); }
	});

	// ---------------------------------------------------------------- bookings & money
	async function bookings(p, q) {
		const status = q.get("status") || ""; const res = await O("bookings_list", { status }); actions();
		return { title: "Bookings", el: h("div", {}, tabsFor("bookings", status, [["", "All"], ["Pending Payment", "Awaiting deposit"], ["Confirmed,Dispatched,On Hire,Off-Hire Requested,Delivered,Mobilized,Active,Returned,Demobilized", "In fulfilment"], ["Completed", "Completed"], ["Cancelled", "Cancelled"]]),
			MP.table([{ label: "Booking", html: (b) => `<b>${esc(b.name)}</b><div class="tiny muted">${esc(b.customer)} ⇄ ${esc(b.vendor)}</div>` }, { label: "Type", key: "transaction_type" }, { label: "Status", html: (b) => MP.badge(b.status) },
				{ label: "Value", html: (b) => MP.money(b.grand_total, b.currency), right: 1 }, { label: "Paid", html: (b) => MP.money(b.amount_paid, b.currency), right: 1 }, { label: "Commission", html: (b) => MP.money(b.commission_amount, b.currency), right: 1 }], res.rows,
				{ onclick: (b) => MP.go(`${BASE}/bookings/${encodeURIComponent(b.name)}`) })) };
	}
	async function booking({ name }) {
		const b = await O("booking_get", { name }), cur = b.currency;
		actions(...b.next_actions.map((a) => btn(a, async () => (await MP.confirm(a + "?", "Operator override — both parties are notified.", a)) && act(() => O("booking_action", { name, action: a }), "Updated"), "btn ghost sm")),
			!["Completed", "Cancelled"].includes(b.status) ? btn("Cancel booking", async () => { const v = await MP.prompt("Cancel booking (operator)", [{ name: "reason", label: "Reason", full: 1, reqd: 1 }], "Cancel"); if (v) act(() => O("booking_action", { name, action: "cancel", data: v }), "Cancelled"); }, "btn red sm") : null);
		return { title: b.name, el: h("div", { class: "stack" }, h("div", { class: "card row between" }, h("div", {}, h("h2", { style: { margin: 0 } }, b.name), h("span", { class: "muted" }, `${b.transaction_type} · ${b.customer} ⇄ ${b.vendor} · offer ${b.offer} rev ${b.offer_revision}`)), h("span", { html: MP.badge(b.status) })),
			h("div", { class: "grid g4" }, [["Total", b.grand_total], ["Paid", b.amount_paid], ["Refunded", b.amount_refunded], ["Commission", b.commission_amount]].map(([k, v]) => h("div", { class: "card kpi" }, h("span", {}, k), h("b", { style: { fontSize: "1.3rem" } }, MP.money(v, cur))))),
			h("div", { class: "grid g2" }, h("div", { class: "card" }, h("h3", {}, "Payments"), MP.table([{ label: "Payment", key: "name" }, { label: "Type", key: "payment_type" }, { label: "Status", html: (x) => MP.badge(x.status) }, { label: "Amount", html: (x) => MP.money(x.amount, x.currency), right: 1 }], b.payments)),
				h("div", { class: "card" }, h("h3", {}, "Schedule"), MP.table([{ label: "Line", key: "line_type" }, { label: "Due", html: (s) => MP.date(s.due_date) }, { label: "Status", html: (s) => MP.badge(s.status) }, { label: "Amount", html: (s) => MP.money(s.amount, cur), right: 1 }], b.schedule))),
			b.vendor_order_doc ? h("div", { class: "card" }, h("h3", {}, "Vendor order"), h("dl", { class: "dl" }, ...[["Order", b.vendor_order_doc.name], ["Status", b.vendor_order_doc.status], ["Fulfilment", b.vendor_order_doc.fulfilment_mode], ["ERP", b.vendor_order_doc.erp_reference ? `${b.vendor_order_doc.erp_reference_doctype} ${b.vendor_order_doc.erp_reference} (${b.vendor_order_doc.erp_status || ""})` : "—"]].flatMap(([k, v]) => [h("dt", {}, k), h("dd", {}, v || "—")]))) : "",
			h("div", { class: "card" }, h("h3", {}, "Audit history"), history(b.history))) };
	}
	async function payments(p, q) {
		const status = q.get("status") || ""; const res = await O("payments_list", { status }); actions();
		return { title: "Payments & refunds", el: h("div", {}, tabsFor("payments", status, [["", "All"], ["Pending", "Awaiting confirmation"], ["Succeeded", "Received"], ["Failed", "Failed"], ["Refunded,Partially Refunded", "Refunded"]]),
			h("p", { class: "small muted" }, "Gateway payments are confirmed only by the provider's signed webhook. Manual (bank transfer) payments and refunds are confirmed here by Finance with a reference."),
			MP.table([{ label: "Payment", html: (x) => `<b>${esc(x.name)}</b><div class="tiny muted">${esc(x.booking || x.subscription || "")}${x.refund_of ? " · refund of " + esc(x.refund_of) : ""}</div>` }, { label: "Type", key: "payment_type" }, { label: "Gateway", key: "gateway" },
				{ label: "Payer ref", key: "payer_reference" }, { label: "Status", html: (x) => MP.badge(x.status) }, { label: "Amount", html: (x) => MP.money(x.amount, x.currency), right: 1 },
				{ label: "", html: (x) => (x.gateway === "Manual" && x.status === "Pending" ? `<button class="btn sm" data-pc="${esc(x.name)}">${x.payment_type === "Refund" ? "Confirm sent" : "Confirm received"}</button> ` : "") + (x.status === "Succeeded" && x.payment_type !== "Refund" && x.payment_type !== "Cancellation Fee" ? `<button class="btn ghost sm" data-pr="${esc(x.name)}" data-max="${x.amount - (x.refunded_amount || 0)}">Refund</button>` : "") }], res.rows)) };
	}
	document.addEventListener("click", async (e) => {
		const c = e.target.closest("[data-pc]"), r = e.target.closest("[data-pr]");
		if (c) { const v = await MP.prompt("Confirm payment", [{ name: "reference", label: "Bank / transfer reference", reqd: 1, full: 1 }], "Confirm"); if (v) act(() => O("payment_confirm", { name: c.dataset.pc, reference: v.reference }), "Confirmed"); }
		if (r) { const v = await MP.prompt("Refund", [{ name: "amount", label: `Amount (max ${r.dataset.max})`, type: "number", reqd: 1, value: r.dataset.max }, { name: "reason", label: "Reason", full: 1 }], "Request refund"); if (v) act(() => O("payment_refund", { name: r.dataset.pr, ...v }), "Refund requested"); }
	});
	async function commissions(p, q) { const status = q.get("status") || ""; const res = await O("commissions_list", { status });
		actions(h("a", { class: "btn ghost sm", href: "/app/commission-rule", target: "_blank" }, "Commission rules"));
		return { title: "Commissions", el: h("div", {}, tabsFor("commissions", status, [["", "All"], ["Accrued", "Accrued"], ["Earned", "Earned"], ["Settled", "Settled"], ["Reversed", "Reversed"]]),
			MP.table([{ label: "Commission", key: "name" }, { label: "Booking", key: "booking" }, { label: "Supplier", key: "vendor" }, { label: "Basis", html: (c) => esc(c.basis === "Percentage" ? c.rate + "%" : "Fixed") }, { label: "Base", html: (c) => MP.money(c.base_amount, c.currency), right: 1 },
				{ label: "Commission", html: (c) => MP.money(c.commission_amount, c.currency), right: 1 }, { label: "Status", html: (c) => MP.badge(c.status) }, { label: "Settlement", key: "settlement" }], res.rows)) }; }
	async function settlements(p, q) {
		const status = q.get("status") || ""; const res = await O("settlements_list", { status });
		actions(btn("Build settlement", async () => { const v = await MP.prompt("Build vendor settlement", [{ name: "vendor", label: "Supplier ID (VND-…)", reqd: 1 }, { name: "period_from", label: "From", type: "date", reqd: 1 }, { name: "period_to", label: "To", type: "date", reqd: 1 }], "Build");
			if (v) act(() => O("settlement_action", { action: "build", ...v }), "Settlement drafted"); }, "btn amber sm"));
		return { title: "Settlements", el: h("div", {}, tabsFor("settlements", status, [["", "All"], ["Draft", "Draft"], ["Approved", "Approved"], ["Paid", "Paid"], ["Cancelled", "Cancelled"]]),
			MP.table([{ label: "Settlement", key: "name" }, { label: "Supplier", key: "vendor" }, { label: "Period", html: (s) => `${MP.date(s.period_from)} → ${MP.date(s.period_to)}` }, { label: "Gross", html: (s) => MP.money(s.gross_amount, s.currency), right: 1 },
				{ label: "Commission", html: (s) => MP.money(s.commission_amount, s.currency), right: 1 }, { label: "Net", html: (s) => `<b>${MP.money(s.net_payable, s.currency)}</b>`, right: 1 }, { label: "Status", html: (s) => MP.badge(s.status) + (s.payout_reference ? `<div class="tiny">${esc(s.payout_reference)}</div>` : "") },
				{ label: "", html: (s) => (s.status === "Draft" ? `<button class="btn sm" data-st="approve" data-n="${esc(s.name)}">Approve</button> <button class="btn ghost sm" data-st="cancel" data-n="${esc(s.name)}">Cancel</button>` : s.status === "Approved" ? `<button class="btn green sm" data-st="paid" data-n="${esc(s.name)}">Record payout</button>` : "") }], res.rows)) };
	}
	document.addEventListener("click", async (e) => { const b = e.target.closest("[data-st]"); if (!b) return;
		let extra = {};
		if (b.dataset.st === "paid") { extra = await MP.prompt("Record payout", [{ name: "payout_reference", label: "Bank / provider payout reference", reqd: 1, full: 1 }], "Mark paid"); if (!extra) return; }
		act(() => O("settlement_action", { action: b.dataset.st, name: b.dataset.n, ...extra }), "Updated"); });
	async function subscriptions(p, q) { const status = q.get("status") || ""; const res = await O("subscriptions_list", { status });
		actions(h("a", { class: "btn ghost sm", href: "/app/marketplace-subscription-plan", target: "_blank" }, "Edit plans"));
		return { title: "Subscriptions", el: h("div", {}, tabsFor("subscriptions", status, [["", "All"], ["Trial", "Trial"], ["Active", "Active"], ["Grace", "Grace"], ["Pending Payment", "Pending payment"], ["Expired", "Expired"]]),
			MP.table([{ label: "Subscription", key: "name" }, { label: "Supplier", key: "vendor" }, { label: "Plan", key: "plan" }, { label: "Change", key: "change_type" }, { label: "Period", html: (s) => `${MP.date(s.start_date)} → ${MP.date(s.end_date)}` }, { label: "Status", html: (s) => MP.badge(s.status) }, { label: "Amount", html: (s) => MP.money(s.amount, s.currency), right: 1 }], res.rows)) }; }

	// ---------------------------------------------------------------- trust & content
	async function listings(p, q) { const status = q.get("status") || ""; const res = await O("listings_list", { status, q: q.get("q") || "" }); actions();
		return { title: "Listings", el: h("div", {}, tabsFor("listings", status, [["", "All"], ["Published", "Published"], ["Suspended", "Suspended"], ["Draft", "Draft"]]),
			MP.table([{ label: "Listing", html: (l) => `<b>${esc(l.title)}</b><div class="tiny muted">${esc(l.vendor)} · ${esc(l.category)}</div>` }, { label: "Status", html: (l) => MP.badge(l.status) + (l.featured ? ' <span class="badge green">Featured</span>' : "") }, { label: "Qty", key: "total_qty", right: 1 },
				{ label: "", html: (l) => `${l.status === "Suspended" ? `<button class="btn ghost sm" data-lm="restore" data-n="${esc(l.name)}">Restore</button>` : `<button class="btn ghost sm" data-lm="suspend" data-n="${esc(l.name)}">Suspend</button>`} <button class="btn ghost sm" data-lm="${l.featured ? "unfeature" : "feature"}" data-n="${esc(l.name)}">${l.featured ? "Unfeature" : "Feature"}</button>` }], res.rows)) }; }
	document.addEventListener("click", (e) => { const b = e.target.closest("[data-lm]"); if (b) act(() => O("listing_moderate", { name: b.dataset.n, action: b.dataset.lm }), "Updated"); });
	async function reviews(p, q) { const status = q.get("status") ?? "Pending Moderation"; const res = await O("reviews_list", { status }); actions();
		return { title: "Reviews", el: h("div", {}, tabsFor("reviews", status, [["Pending Moderation", "To moderate"], ["Published", "Published"], ["Hidden", "Hidden"]]),
			MP.table([{ label: "Review", html: (r) => `<span class="stars">${MP.stars(r.rating * 5)}</span> <b>${esc(r.title || "")}</b><div class="small">${esc(r.comment || "")}</div>` }, { label: "Supplier", key: "vendor" }, { label: "Booking", key: "booking" }, { label: "Status", html: (r) => MP.badge(r.status) },
				{ label: "", html: (r) => `<button class="btn sm" data-rm="Published" data-n="${esc(r.name)}">Publish</button> <button class="btn ghost sm" data-rm="Hidden" data-n="${esc(r.name)}">Hide</button>` }], res.rows)) }; }
	document.addEventListener("click", (e) => { const b = e.target.closest("[data-rm]"); if (b) act(() => O("review_moderate", { name: b.dataset.n, status: b.dataset.rm }), "Review " + b.dataset.rm.toLowerCase()); });
	async function disputes(p, q) { const status = q.get("status") || "Open,Under Review,Escalated"; const res = await O("disputes_list", { status }); actions();
		return { title: "Disputes", el: h("div", {}, tabsFor("disputes", status, [["Open,Under Review,Escalated", "Open"], ["Resolved,Rejected", "Closed"], ["", "All"]]),
			MP.table([{ label: "Dispute", key: "name" }, { label: "Booking", key: "booking" }, { label: "Raised by", key: "raised_by_party" }, { label: "Type", key: "dispute_type" }, { label: "Claimed", html: (d) => MP.money(d.claimed_amount), right: 1 }, { label: "Status", html: (d) => MP.badge(d.status) }], res.rows,
				{ onclick: (d) => MP.go(`${BASE}/disputes/${encodeURIComponent(d.name)}`) })) }; }
	async function dispute({ name }) {
		const d = await O("dispute_get", { name }), bi = d.booking_info;
		actions(!["Resolved", "Rejected"].includes(d.status) ? btn("Resolve", async () => { const v = await MP.prompt("Resolve dispute", [{ name: "status", label: "Outcome", type: "select", options: ["Resolved", "Rejected", "Escalated", "Under Review"] }, { name: "refund_amount", label: `Refund to customer (paid ${bi.amount_paid})`, type: "number", value: 0 },
			{ name: "resolution", label: "Resolution", type: "textarea", full: 1, reqd: 1 }], "Save"); if (v) act(() => O("dispute_resolve", { name, ...v }), "Saved"); }, "btn sm") : null);
		return { title: d.name, el: h("div", { class: "stack" }, h("div", { class: "card" }, h("div", { class: "row between" }, h("h3", {}, `${d.dispute_type} · ${d.booking}`), h("span", { html: MP.badge(d.status) })), h("p", {}, d.description),
			h("dl", { class: "dl" }, h("dt", {}, "Raised by"), h("dd", {}, `${d.raised_by_party} (${d.raised_by})`), h("dt", {}, "Claimed"), h("dd", {}, MP.money(d.claimed_amount, bi.currency)), h("dt", {}, "Booking"), h("dd", {}, h("a", { href: `${BASE}/bookings/${d.booking}` }, `${d.booking} · ${bi.status} · ${MP.money(bi.grand_total, bi.currency)}`)),
				d.evidence ? [h("dt", {}, "Evidence"), h("dd", {}, h("a", { href: MP.fileLink(d.evidence), target: "_blank" }, "📎 file"))] : "", d.resolution ? [h("dt", {}, "Resolution"), h("dd", {}, d.resolution)] : ""))) };
	}
	async function enquiries() { const res = await O("enquiries"); actions(); return { title: "Enquiries", el: MP.table([{ label: "From", html: (e) => `<b>${esc(e.full_name)}</b><div class="tiny muted">${esc(e.email)} · ${esc(e.company || "")}</div>` }, { label: "Topic", key: "enquiry_type" }, { label: "Message", key: "message" }, { label: "Received", html: (e) => MP.dt(e.creation) }], res.rows) }; }
	async function audit(p, q) { const res = await O("audit_trail", { doctype: q.get("doctype") || "", name: q.get("name") || "" }); actions();
		const f = h("form", { class: "row", style: { marginBottom: "14px" } }, h("input", { name: "doctype", placeholder: "DocType (e.g. Supplier Offer)", value: q.get("doctype") || "" }), h("input", { name: "name", placeholder: "Document ID", value: q.get("name") || "" }), h("button", { class: "btn sm" }, "Filter"));
		f.onsubmit = (e) => { e.preventDefault(); MP.go(`${BASE}/audit?doctype=${encodeURIComponent(f.doctype.value)}&name=${encodeURIComponent(f.name.value)}`); };
		return { title: "Audit trail", el: h("div", {}, f, MP.table([{ label: "When", html: (e) => MP.dt(e.creation) }, { label: "Event", key: "event" }, { label: "Document", html: (e) => esc(`${e.reference_doctype || ""} ${e.reference_name || ""}`) }, { label: "Transition", html: (e) => esc(e.from_state || e.to_state ? `${e.from_state || ""} → ${e.to_state || ""}` : "") }, { label: "Actor", key: "actor" }, { label: "Data", html: (e) => `<span class="tiny muted">${esc((e.data || "").slice(0, 160))}</span>` }], res.rows)) }; }
	async function settings() { actions();
		const links = [["Marketplace Settings", "/app/marketplace-settings", "Tender defaults, deposits, payment gateway keys, rental engine integration, homepage content, legal pages"], ["Categories & attributes", "/app/marketplace-category/view/tree", "Dynamic equipment category tree and required attributes"],
			["Commission rules", "/app/commission-rule", "Percentage / fixed, by category, transaction type, plan or supplier"], ["Subscription plans", "/app/marketplace-subscription-plan", "Prices, listing / response / user limits"], ["Evaluation criteria", "/app/offer-evaluation-criterion", "Weighted scoring criteria"],
			["Promotions", "/app/marketplace-promotion", "Featured suppliers, listings, tenders"], ["Webhook log", "/app/marketplace-webhook-event", "Verified payment provider events"]];
		return { title: "Configuration", el: h("div", { class: "grid g3" }, links.map(([t, href, d]) => h("a", { class: "card hover", href, target: "_blank" }, h("h3", {}, t), h("p", { class: "small muted" }, d)))) }; }

	MP.portal({ base: BASE, routes: { "": analytics, vendors, "vendors/:name": vendor, customers, tenders, "tenders/:name": tender, bookings, "bookings/:name": booking, payments, commissions, settlements, subscriptions, listings, reviews, disputes, "disputes/:name": dispute, enquiries, audit, settings } });
	O("notifications").then((n) => MP.setBell(n.unread)).catch(() => {});
})();
