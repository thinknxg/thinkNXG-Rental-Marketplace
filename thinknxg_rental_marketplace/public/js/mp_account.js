/* Customer workspace: requirements, tender tracking, offer comparison, bookings, payments, reviews. */
(function () {
	const h = MP.h, esc = MP.esc, C = (m, a) => MP.call("customer." + m, a), BASE = "/marketplace/account";
	const nav = [["", "home", "Overview", "^$"], ["requests", "doc", "Requirements", "^requests|^tenders"], ["bookings", "box", "Bookings", "^bookings|^payments"],
		["sites", "pin", "Project sites", "^sites"], ["profile", "users", "Company & users", "^profile"]];
	MP.$("#side-nav").innerHTML = '<div class="sec">Procurement</div>' + nav.map(([p, i, l, m]) => `<a href="${BASE}/${p}" data-match="${m}">${MP.icon(i)}${l}</a>`).join("") +
		`<div class="sec">Actions</div><a href="/marketplace/post-requirement" data-full>${MP.icon("plus")}Post a requirement</a><a href="/marketplace/equipment" data-full>${MP.icon("grid")}Browse equipment</a>`;
	MP.$(".bell").onclick = () => MP.notifPanel("customer");
	const actions = (...els) => { const b = MP.$("#bar-actions"); b.innerHTML = ""; els.forEach((e) => b.append(e)); };
	const link = (href, label, cls = "btn sm") => h("a", { class: cls, href }, label);
	const need = async () => { try { return await C("dashboard"); } catch (e) { if (e.code === "NOT_A_CUSTOMER") { location.href = "/marketplace/register"; } throw e; } };

	const TENDER_FLOW = ["Submitted", "Published", "Bidding Open", "Bidding Closed", "Evaluation", "Awarded"];
	const flow = (steps, cur) => { const i = steps.indexOf(cur); return `<div class="status-steps">${steps.map((s, j) => `<span class="${j < i ? "done" : j === i ? "now" : ""}">${s}</span>`).join("")}</div>`; };

	async function overview() {
		const d = await need();
		actions(link("/marketplace/post-requirement", "Post a requirement", "btn amber sm"));
		MP.setBell(d.notifications.unread);
		const c = d.counts;
		return { title: "Overview", el: h("div", { class: "stack" },
			h("div", { class: "row between" }, h("div", {}, h("h2", { style: { margin: 0 } }, "Welcome, " + (d.customer.customer_name || "")), h("span", { class: "muted small" }, [d.customer.city, d.customer.country].filter(Boolean).join(", "), d.customer.verified ? " · ✔ verified buyer" : ""))),
			MP.kpis([{ label: "Open requirements", value: c.open_requests, href: BASE + "/requests" }, { label: "Tenders live", value: c.live_tenders, href: BASE + "/requests" },
				{ label: "Ready to compare", value: c.to_evaluate, href: BASE + "/requests" }, { label: "Active bookings", value: c.active_bookings, href: BASE + "/bookings" }]),
			c.pending_payment ? h("div", { class: "card", style: { background: "var(--amber-soft)", borderColor: "#f3d18f" } }, h("b", {}, `${c.pending_payment} booking(s) waiting for a deposit — stock is held for a limited time.`), " ", link(BASE + "/bookings", "Pay now")) : "",
			h("div", { class: "grid g2" },
				h("div", { class: "stack" }, h("h3", {}, "Recent requirements"), reqTable(d.recent_requests)),
				h("div", { class: "stack" }, h("h3", {}, "Recent bookings"), bookingTable(d.recent_bookings)))) };
	}
	const reqTable = (rows) => MP.table([{ label: "Reference", html: (r) => `<a href="${BASE}/requests/${esc(r.name)}"><b>${esc(r.name)}</b></a><div class="small muted">${esc(r.title)}</div>` },
		{ label: "Type", key: "transaction_type" }, { label: "Status", html: (r) => MP.badge(r.status) }, { label: "Created", html: (r) => MP.date(r.creation) }], rows,
		{ onclick: (r) => MP.go(`${BASE}/requests/${encodeURIComponent(r.name)}`), empty: "No requirements yet — post one to get offers." });
	const bookingTable = (rows) => MP.table([{ label: "Booking", html: (r) => `<a href="${BASE}/bookings/${esc(r.name)}"><b>${esc(r.name)}</b></a><div class="small muted">${esc(r.vendor_name || r.project_name || "")}</div>` },
		{ label: "Type", key: "transaction_type" }, { label: "Status", html: (r) => MP.badge(r.status) }, { label: "Total", html: (r) => MP.money(r.grand_total, r.currency), right: 1 }], rows,
		{ onclick: (r) => MP.go(`${BASE}/bookings/${encodeURIComponent(r.name)}`), empty: "No bookings yet." });

	async function requestsList(p, q) {
		const status = q.get("status") || "";
		const res = await C("requests_list", { status, page: q.get("page") || 1 });
		actions(link("/marketplace/post-requirement", "New requirement", "btn amber sm"));
		const tabs = ["", "Draft", "Tendered", "Offers Received", "Awarded", "Booked", "Closed", "Cancelled"];
		return { title: "Requirements", el: h("div", {}, h("div", { class: "tabs" }, tabs.map((t) => h("a", { href: `${BASE}/requests${t ? "?status=" + encodeURIComponent(t) : ""}`, class: t === status ? "on" : "" }, t || "All"))), reqTable(res.rows)) };
	}

	async function requestDetail({ name }) {
		const r = await C("request_get", { name });
		const t = r.tender_info;
		const el = h("div", { class: "stack" });
		actions(...[
			t && ["Evaluation", "Bidding Closed", "Awarded"].includes(t.status) ? link(`${BASE}/tenders/${encodeURIComponent(t.name)}/compare`, `Compare ${t.offers_count} offers`, "btn amber sm") : null,
			t && ["Bidding Open"].includes(t.status) ? h("button", { class: "btn ghost sm", onclick: () => closeEarly(t.name) }, "Close bidding early") : null,
			t && ["Bidding Open", "Expired", "Bidding Closed", "Evaluation"].includes(t.status) ? h("button", { class: "btn ghost sm", onclick: () => extend(t.name) }, "Extend deadline") : null,
			!["Booked", "Closed", "Cancelled"].includes(r.status) ? h("button", { class: "btn ghost sm", onclick: () => cancelReq(name) }, "Cancel") : null,
		].filter(Boolean));
		el.append(h("div", { class: "card" }, h("div", { class: "row between" }, h("div", {}, h("span", { class: "eyebrow" }, r.transaction_type + " · " + r.category), h("h2", { style: { margin: "6px 0" } }, r.title), h("span", { class: "muted" }, r.name)), h("div", { html: MP.badge(r.status) })),
			t ? h("div", { style: { marginTop: "16px" }, html: flow(TENDER_FLOW, t.status === "Invitation Sent" ? "Bidding Open" : t.status) }) : ""));
		if (t) el.append(h("div", { class: "grid g4" }, [["Tender", t.name], ["Suppliers invited", t.invited_count], ["Offers received", t.offers_count], [t.status === "Bidding Open" ? "Closes" : "Deadline", t.status === "Bidding Open" ? MP.until(t.submission_deadline) : MP.dt(t.submission_deadline)]]
			.map(([k, v]) => h("div", { class: "card kpi" }, h("span", {}, k), h("b", { style: { fontSize: "1.4rem" } }, v)))));
		if (t && t.status === "Bidding Open" && t.confidentiality !== "Open") el.append(h("div", { class: "card small", style: { background: "var(--blue-soft)" } }, "🔒 Sealed bidding: offers are opened when the deadline passes (or when you close bidding early after every invited supplier responded)."));
		const period = r.transaction_type === "Hire" ? `${MP.date(r.required_from)} → ${MP.date(r.required_to)} · ${r.duration_days} days` : r.transaction_type === "Sale" ? `Deliver by ${MP.date(r.expected_delivery_date)}` : `${MP.date(r.contract_start)} · ${r.contract_months} months`;
		el.append(h("div", { class: "grid g2" },
			h("div", { class: "card" }, h("h3", {}, "Equipment"), MP.table([{ label: "Item", html: (i) => `<b>${esc(i.equipment_name)}</b><div class="small muted">${esc(i.specifications || "")}</div>` }, { label: "Qty", html: (i) => esc(i.qty + " " + i.uom), right: 1 }], r.items),
				h("dl", { class: "dl", style: { marginTop: "14px" } }, h("dt", {}, "Period"), h("dd", {}, period), h("dt", {}, "Budget"), h("dd", {}, r.budget_max ? `${MP.money(r.budget_min || 0, r.currency)} – ${MP.money(r.budget_max, r.currency)}` : "Not specified"))),
			h("div", { class: "card" }, h("h3", {}, "Site"), h("dl", { class: "dl" }, ...[["Project", r.project_name], ["Address", r.site_address], ["City", [r.city, r.state, r.country].filter(Boolean).join(", ")], ["Contact", [r.site_contact, r.site_phone].filter(Boolean).join(" · ")]].flatMap(([k, v]) => [h("dt", {}, k), h("dd", {}, v || "—")])),
				r.attachments.length ? h("div", { style: { marginTop: "14px" } }, h("h4", {}, "Documents"), r.attachments.map((a) => h("div", {}, h("a", { href: MP.fileLink(a.file), target: "_blank" }, "📎 " + (a.title || a.document_type)), a.share_with_suppliers ? h("span", { class: "tiny muted" }, " · shared with invited suppliers") : ""))) : "")));
		if (r.booking) el.append(h("div", { class: "card row between" }, h("b", {}, "Booked as " + r.booking), link(`${BASE}/bookings/${encodeURIComponent(r.booking)}`, "Open booking")));
		el.append(h("div", { class: "card" }, h("h3", {}, "Activity"), h("div", { class: "timeline" }, r.history.map((e) => h("div", {}, h("b", {}, e.event), e.to_state ? " → " + e.to_state : "", h("span", { class: "muted" }, " · " + MP.dt(e.creation)))))));
		return { title: r.name, el };
	}
	async function closeEarly(tender) { if (await MP.confirm("Close bidding early?", "Offers open now. Only possible once every invited supplier has responded.", "Close bidding")) { await MP.safe(() => C("tender_close_early", { tender }), "Bidding closed"); MP.reload(); } }
	async function extend(tender) { const v = await MP.prompt("Extend submission deadline", [{ name: "deadline", label: "New deadline", type: "datetime-local", reqd: 1 }, { name: "reason", label: "Reason", full: 1 }]);
		if (v) { await MP.safe(() => C("tender_extend", { tender, deadline: v.deadline.replace("T", " ") + ":00", reason: v.reason }), "Deadline extended — suppliers notified"); MP.reload(); } }
	async function cancelReq(name) { const v = await MP.prompt("Cancel requirement", [{ name: "reason", label: "Reason", full: 1, reqd: 1 }], "Cancel requirement"); if (v) { await MP.safe(() => C("request_cancel", { name, reason: v.reason }), "Cancelled"); MP.reload(); } }

	// ---------------------------------------------------------------- offer comparison
	async function compare({ name }) {
		const d = await C("compare", { tender: name });
		const T = d.tender, el = h("div", { class: "stack" });
		actions(link(`${BASE}/requests`, "All requirements", "btn ghost sm"));
		el.append(h("div", { class: "card row between" }, h("div", {}, h("span", { class: "eyebrow" }, T.transaction_type + " · " + T.name), h("h2", { style: { margin: "4px 0" } }, T.title),
			h("span", { class: "muted small" }, T.transaction_type === "Hire" ? `${MP.date(T.required_from)} → ${MP.date(T.required_to)} (${T.duration_days} days)` : T.transaction_type === "Contract" ? `${T.contract_months} months` : "Purchase")),
			h("div", { class: "row" }, h("span", { html: MP.badge(T.status) }), h("span", { class: "badge" }, `${T.offers_count} offers / ${T.invited_count} invited`), h("span", { class: "badge blue" }, T.evaluation_method))));
		if (d.sealed) { el.append(h("div", { class: "empty" }, h("h3", {}, "Offers are sealed until bidding closes"), h("p", {}, `${T.offers_count} offer(s) received so far. Closes ${MP.dt(T.submission_deadline)} (${MP.until(T.submission_deadline)}).`))); return { title: "Compare offers", el }; }
		if (!d.offers.length) { el.append(h("div", { class: "empty" }, "No offers to compare.")); return { title: "Compare offers", el }; }
		let sort = "price";
		const grid = h("div", { class: "compare" });
		const sorters = { price: (a, b) => a.comparable_total - b.comparable_total, delivery: (a, b) => String(a.delivery_date).localeCompare(String(b.delivery_date)),
			rating: (a, b) => (b.vendor.rating || 0) - (a.vendor.rating || 0), score: (a, b) => (b.score || 0) - (a.score || 0) };
		const draw = () => { grid.innerHTML = ""; [...d.offers].sort(sorters[sort]).forEach((o) => grid.append(offerCard(o, T, d))); };
		el.append(h("div", { class: "row between" }, h("div", { class: "modes" }, Object.keys(sorters).filter((k) => k !== "score" || d.criteria).map((k) => h("button", { class: k === sort ? "on" : "", onclick: (e) => { sort = k; MP.$$(".modes button", el).forEach((b) => b.classList.toggle("on", b === e.target)); draw(); } }, "Sort: " + k))),
			h("span", { class: "small muted" }, "The lowest price is highlighted, never chosen for you.")));
		el.append(grid); draw();
		if (d.criteria) el.append(h("div", { class: "card small" }, h("b", {}, "Weighted scoring: "), d.criteria.map((c) => `${c.criterion} ${c.weight}%`).join(" · "), h("div", { class: "muted" }, "Price: lowest ÷ offer × 100 · Delivery: earliest scores 100 · Rating: stars ÷ 5 × 100 · Technical: Full 100 / Partial 60 / Alternative 50.")));
		el.append(h("div", { class: "card" }, h("h3", {}, "Line-by-line technical comparison"), lineMatrix(d)));
		el.append(h("div", { class: "card" }, h("div", { class: "row between" }, h("h3", {}, "Clarifications & negotiation"), h("button", { class: "btn ghost sm", onclick: () => clarify(T.name, null, d.offers) }, "Ask all suppliers")),
			d.clarifications.length ? h("div", { class: "stack" }, d.clarifications.map((c) => h("div", { class: "card flat" }, h("div", { class: "row between" }, h("b", {}, c.subject), h("span", { html: MP.badge(c.status) + ` <span class="badge">${esc(c.clarification_type)}</span>` })),
				h("p", { class: "small" }, c.message), c.counter_amount ? h("div", { class: "small" }, "Counter-offer: " + MP.money(c.counter_amount, T.currency)) : "", c.response ? h("div", { class: "small", style: { background: "var(--steel-50)", padding: "8px", borderRadius: "8px" } }, h("b", {}, "Response: "), c.response) : "",
				c.status === "Open" && c.raised_by_party === "Supplier" ? h("button", { class: "btn sm", onclick: () => respond(c) }, "Reply") : "")))
				: h("p", { class: "muted" }, "No clarifications yet.")));
		return { title: "Compare offers", el };
	}
	function offerCard(o, T, d) {
		const live = ["Submitted", "Under Review", "Technically Accepted", "Commercially Accepted"].includes(o.status);
		const v = o.vendor, cur = o.currency;
		const line = (k, val) => h("div", { class: "line" }, h("span", {}, k), h("span", {}, val));
		const card = h("div", { class: "card offer" + (o.shortlisted ? " short" : "") },
			h("div", { class: "flags" }, (o.flags || []).map((f) => h("span", { class: "badge green" }, f)), o.shortlisted ? h("span", { class: "badge amber" }, "★ Shortlisted") : "", h("span", { html: MP.badge(o.status) })),
			h("div", { class: "scard" }, h("div", { class: "avatar", style: v.logo ? { backgroundImage: `url('${v.logo}')` } : null }, v.logo ? "" : (v.business_name || "?")[0]),
				h("div", {}, h("b", {}, v.business_name), h("div", { class: "small" }, v.verified ? h("span", { class: "verified" }, "✔ Verified · ") : "", v.review_count ? h("span", { class: "stars" }, MP.stars(v.rating)) : h("span", { class: "muted" }, "New supplier")), h("div", { class: "tiny muted" }, [v.city, v.country].filter(Boolean).join(", ")))),
			h("div", {}, h("div", { class: "total" }, MP.money(o.grand_total, cur)), h("div", { class: "tiny muted" }, `incl. tax · revision ${o.revision_no}`)),
			o.score !== undefined ? h("div", {}, h("div", { class: "row between small" }, h("span", {}, "Score"), h("b", {}, o.score)), h("div", { class: "score-bar" }, h("i", { style: { width: o.score + "%" } }))) : "",
			line("Equipment", MP.money(o.subtotal, cur)), line("Delivery & other charges", MP.money(o.charges_total, cur)), line("Tax", `${MP.money(o.tax_amount, cur)} (${o.tax_percent || 0}%)`),
			line("Security deposit (refundable)", MP.money(o.security_deposit, cur)), line("Delivery date", MP.date(o.delivery_date)), line("Technical compliance", o.technical_compliance || "—"),
			line("Payment terms", o.payment_terms || "—"), line("Valid until", MP.date(o.valid_until)),
			o.missing.length ? h("div", { class: "missing" }, "Missing / short: " + o.missing.join("; ")) : "",
			h("details", {}, h("summary", { class: "small", style: { cursor: "pointer", color: "var(--blue)" } }, "Commercial detail"), MP.table([{ label: "Line", html: (i) => `${esc(i.equipment_name)}${i.is_alternative ? ' <span class="badge amber">Alternative</span>' : ""}<div class="tiny muted">${esc(i.alternative_details || i.remarks || "")}</div>` },
				{ label: "Qty", key: "qty", right: 1 }, { label: "Rate", html: (i) => `${MP.money(i.unit_rate, cur)}<div class="tiny muted">${esc(i.rate_basis)} × ${i.periods}</div>`, right: 1 }, { label: "Amount", html: (i) => MP.money(i.amount, cur), right: 1 }], o.items),
				h("dl", { class: "dl small", style: { marginTop: "8px" } }, h("dt", {}, "Transport"), h("dd", {}, MP.money(o.transport_charges, cur)), h("dt", {}, "Loading"), h("dd", {}, MP.money(o.loading_charges, cur)), h("dt", {}, "Installation"), h("dd", {}, MP.money(o.installation_charges, cur)),
					h("dt", {}, "Mobilisation"), h("dd", {}, MP.money((o.mobilization_charges || 0) + (o.demobilization_charges || 0), cur)), h("dt", {}, "Conditions"), h("dd", {}, o.commercial_conditions || "—"), h("dt", {}, "Compliance notes"), h("dd", {}, o.compliance_notes || "—"))),
			live && T.status !== "Awarded" ? h("div", { class: "stack", style: { marginTop: "auto" } },
				h("button", { class: "btn amber block", onclick: () => accept(o, T) }, "Accept this offer"),
				h("div", { class: "row" }, h("button", { class: "btn ghost sm", onclick: async () => { await MP.safe(() => C("offer_shortlist", { offer: o.name, value: o.shortlisted ? 0 : 1 })); MP.reload(); } }, o.shortlisted ? "Unshortlist" : "Shortlist"),
					h("button", { class: "btn ghost sm", onclick: () => clarify(T.name, o.name, d.offers) }, "Clarify / negotiate"), h("button", { class: "btn ghost sm", onclick: () => rejectOffer(o) }, "Reject"))) : "");
		return card;
	}
	function lineMatrix(d) {
		const live = d.offers.filter((o) => !["Rejected", "Technically Rejected"].includes(o.status));
		return h("div", { class: "table-wrap" }, h("table", { class: "t" }, h("thead", {}, h("tr", {}, h("th", {}, "Requirement"), live.map((o) => h("th", {}, o.vendor.business_name)))),
			h("tbody", {}, d.items.map((ti) => h("tr", {}, h("td", {}, h("b", {}, ti.equipment_name), h("div", { class: "tiny muted" }, `${ti.qty} ${ti.uom} · ${ti.specifications || ""}`)),
				live.map((o) => { const ls = o.items.filter((i) => i.tender_item === ti.name);
					return h("td", { html: ls.length ? ls.map((i) => `${esc(i.qty)} × ${MP.money(i.unit_rate, o.currency)}<br><span class="badge ${i.compliance === "Compliant" ? "green" : i.compliance === "Partial" ? "amber" : "red"}">${esc(i.compliance)}</span>${i.is_alternative ? ' <span class="badge amber">Alt</span>' : ""}`).join("<hr>") : '<span class="badge red">Not offered</span>' }); }))))));
	}
	async function accept(o, T) {
		const ok = await MP.modal({ title: "Accept " + o.vendor.business_name + "?", body: `<p>This awards the tender, reserves the supplier's quantity for your dates and creates a booking for <b>${MP.money(o.grand_total, o.currency)}</b>${o.security_deposit ? ` plus a refundable deposit of <b>${MP.money(o.security_deposit, o.currency)}</b>` : ""}.</p><p class="small muted">An advance is requested to confirm. Other suppliers are notified that the tender was awarded; their prices are never shared.</p>`,
			actions: [{ label: "Back", class: "ghost", value: false }, { label: "Accept & book", class: "amber", value: true }] });
		if (!ok) return;
		const r = await MP.safe(() => C("accept_offer", { offer: o.name, idempotency_key: MP.uuid() }), "Booking created");
		MP.go(`${BASE}/bookings/${encodeURIComponent(r.booking)}`);
	}
	async function rejectOffer(o) { const v = await MP.prompt("Reject offer", [{ name: "reason", label: "Reason (shared with the supplier)", full: 1 }], "Reject"); if (v) { await MP.safe(() => C("offer_reject", { offer: o.name, reason: v.reason }), "Offer rejected"); MP.reload(); } }
	async function clarify(tender, offer, offers) {
		const types = offer ? ["Clarification", "Technical", "Commercial", "Counteroffer", "Revision Request"] : ["Clarification", "Technical", "Commercial"];
		const v = await MP.prompt(offer ? "Message this supplier" : "Ask all invited suppliers", [{ name: "clarification_type", label: "Type", type: "select", options: types }, { name: "subject", label: "Subject", reqd: 1 },
			{ name: "message", label: "Message", type: "textarea", full: 1, reqd: 1 }, ...(offer ? [{ name: "counter_amount", label: "Counter-offer total (optional)", type: "number" }] : [])], "Send");
		if (v) { await MP.safe(() => C("clarification_raise", { tender, offer, ...v }), "Sent — recorded against the tender"); MP.reload(); }
	}
	async function respond(c) { const v = await MP.prompt("Reply: " + c.subject, [{ name: "response", label: "Answer", type: "textarea", full: 1, reqd: 1 }, { name: "share_with_all", label: "Share answer (anonymously) with all invited suppliers", type: "check", full: 1 }], "Send reply");
		if (v) { await MP.safe(() => C("clarification_respond", { name: c.name, ...v }), "Reply sent"); MP.reload(); } }

	// ---------------------------------------------------------------- bookings
	async function bookingsList(p, q) { const res = await C("bookings_list", { status: q.get("status") || "" }); actions(); return { title: "Bookings", el: bookingTable(res.rows) }; }
	const BFLOW = { Hire: ["Pending Payment", "Confirmed", "Dispatched", "On Hire", "Off-Hire Requested", "Returned", "Completed"], Sale: ["Pending Payment", "Confirmed", "Dispatched", "Delivered", "Completed"],
		Contract: ["Pending Payment", "Confirmed", "Mobilized", "Active", "Demobilized", "Completed"] };
	async function bookingDetail({ name }) {
		const b = await C("booking_get", { name }), cur = b.currency, el = h("div", { class: "stack" });
		const act = (label, action, cls = "btn sm", fields) => h("button", { class: cls, onclick: async () => {
			let data = {};
			if (fields) { data = await MP.prompt(label, fields, label); if (!data) return; }
			else if (!(await MP.confirm(label + "?", "This updates the booking for both parties.", label))) return;
			await MP.safe(() => C("booking_action", { name, action, data }), "Updated"); MP.reload(); } }, label);
		const labels = { "On Hire": "Confirm delivery received", Delivered: "Confirm delivery received", Active: "Confirm mobilised on site", "Off-Hire Requested": "Request off-hire" };
		actions(...b.next_actions.map((a) => act(labels[a] || a, a, "btn sm", a === "Off-Hire Requested" ? [{ name: "return_date", label: "Collection date", type: "date", reqd: 1 }] : null)),
			b.transaction_type !== "Sale" && ["Confirmed", "Dispatched", "On Hire", "Mobilized", "Active"].includes(b.status) ? act("Request extension", "extension", "btn ghost sm", [{ name: "new_end", label: "New end date", type: "date", reqd: 1 }]) : "",
			b.can_cancel ? act("Cancel booking", "cancel", "btn ghost sm", [{ name: "reason", label: "Reason", full: 1, reqd: 1 }]) : "");
		el.append(h("div", { class: "card" }, h("div", { class: "row between" }, h("div", {}, h("span", { class: "eyebrow" }, b.transaction_type + " booking"), h("h2", { style: { margin: "4px 0" } }, b.name), h("span", { class: "muted" }, b.project_name || "")), h("div", { html: MP.badge(b.status) })),
			h("div", { style: { marginTop: "14px" }, html: flow(BFLOW[b.transaction_type], b.status) })));
		if (b.status === "Pending Payment") {
			const due = b.schedule.filter((s) => ["Advance", "Deposit"].includes(s.line_type) && s.status !== "Paid");
			const pend = b.payments.find((p) => ["Pending", "Initiated"].includes(p.status));
			el.append(h("div", { class: "card", style: { background: "var(--amber-soft)", borderColor: "#f3d18f" } }, h("h3", {}, "Confirm your booking"),
				h("p", {}, `Pay ${MP.money(b.deposit_required, cur)} by ${MP.dt(b.payment_due_by)} — the supplier's stock is reserved until then.`),
				pend ? link(pend.checkout_url || `${BASE}/payments/${pend.name}`, "Continue to payment", "btn amber") : h("button", { class: "btn amber", onclick: async () => { const r = await MP.safe(() => C("pay", { booking: name, lines: due.map((x) => x.name) })); location.href = r.checkout_url; } }, "Pay now")));
		}
		const v = b.vendor_info, vo = b.vendor_order || {};
		el.append(h("div", { class: "grid g2" },
			h("div", { class: "card" }, h("h3", {}, "Supplier"), h("dl", { class: "dl" }, h("dt", {}, "Business"), h("dd", {}, h("a", { href: "/marketplace/suppliers/" + v.route, "data-full": 1 }, v.business_name), v.verified ? " ✔" : ""),
				...(v.email ? [h("dt", {}, "Contact"), h("dd", {}, `${v.contact_person || ""} · ${v.phone || ""} · ${v.email}`)] : [h("dt", {}, "Contact"), h("dd", { class: "muted" }, "Shared after confirmation")]),
				h("dt", {}, "Period"), h("dd", {}, b.transaction_type === "Sale" ? "Delivery " + MP.date(b.delivery_date) : `${MP.date(b.start_date)} → ${MP.date(b.end_date)}${b.extension_days ? ` (+${b.extension_days}d extension)` : ""}`),
				h("dt", {}, "Dispatch"), h("dd", {}, vo.dispatched_on ? `${MP.dt(vo.dispatched_on)} ${vo.vehicle_details ? "· " + vo.vehicle_details : ""}` : "—"), h("dt", {}, "Delivered"), h("dd", {}, MP.dt(vo.delivered_on)),
				h("dt", {}, "Return due"), h("dd", {}, MP.date(vo.return_due)))),
			h("div", { class: "card" }, h("h3", {}, "Amounts"), h("dl", { class: "dl" }, ...[["Equipment", b.subtotal], ["Charges", b.charges_total], ["Tax", b.tax_amount], ["Total", b.grand_total], ["Refundable deposit", b.security_deposit], ["Additional charges", b.additional_charges], ["Paid", b.amount_paid], ["Refunded", b.amount_refunded], ["Balance due", b.balance_due]]
				.flatMap(([k, val]) => [h("dt", {}, k), h("dd", {}, MP.money(val, cur))])))));
		el.append(h("div", { class: "card" }, h("h3", {}, "Equipment"), MP.table([{ label: "Item", key: "equipment_name" }, { label: "Qty", html: (i) => esc(i.qty + " " + (i.uom || "")), right: 1 }, { label: "Rate", html: (i) => `${MP.money(i.unit_rate, cur)} <span class="tiny muted">${esc(i.rate_basis)} × ${i.periods}</span>`, right: 1 },
			{ label: "Amount", html: (i) => MP.money(i.amount, cur), right: 1 }, { label: "Returned / damaged / lost", html: (i) => (i.returned_qty || i.lost_qty ? `${i.returned_qty} / ${i.damaged_qty} / ${i.lost_qty}` : "—") }], b.items)));
		const payable = b.schedule.filter((s) => s.status === "Pending");
		el.append(h("div", { class: "card" }, h("div", { class: "row between" }, h("h3", {}, "Payment schedule"), payable.length && b.status !== "Pending Payment" ? h("button", { class: "btn sm", onclick: async () => { const r = await MP.safe(() => C("pay", { booking: name, lines: payable.map((x) => x.name) })); location.href = r.checkout_url; } }, `Pay ${MP.money(payable.reduce((a, s) => a + s.amount, 0), cur)}`) : ""),
			MP.table([{ label: "Line", key: "line_type" }, { label: "Due", html: (s) => MP.date(s.due_date) }, { label: "Status", html: (s) => MP.badge(s.status) }, { label: "Amount", html: (s) => MP.money(s.amount, cur), right: 1 }], b.schedule),
			h("h4", { style: { marginTop: "16px" } }, "Payment history"), MP.table([{ label: "Payment", html: (p) => `<a href="${BASE}/payments/${esc(p.name)}">${esc(p.name)}</a>` }, { label: "Type", key: "payment_type" }, { label: "Status", html: (p) => MP.badge(p.status) }, { label: "Amount", html: (p) => MP.money(p.amount, p.currency), right: 1 }], b.payments, { empty: "No payments yet." })));
		if (b.can_review) el.append(h("div", { class: "card row between" }, h("b", {}, "How did it go? Your review helps other buyers."), h("button", { class: "btn amber sm", onclick: () => review(name) }, "Write a review")));
		el.append(h("div", { class: "grid g2" }, h("div", { class: "card" }, h("div", { class: "row between" }, h("h3", {}, "Disputes"), !["Pending Payment", "Cancelled"].includes(b.status) ? h("button", { class: "btn ghost sm", onclick: () => dispute(name) }, "Raise a dispute") : ""),
			b.disputes.length ? MP.table([{ label: "Dispute", key: "name" }, { label: "Type", key: "dispute_type" }, { label: "Status", html: (x) => MP.badge(x.status) }, { label: "Resolution", key: "resolution" }], b.disputes) : h("p", { class: "muted small" }, "None.")),
			h("div", { class: "card" }, h("h3", {}, "Activity"), h("div", { class: "timeline" }, b.history.map((e) => h("div", {}, h("b", {}, e.event), e.to_state ? " → " + e.to_state : "", h("span", { class: "muted" }, " · " + MP.dt(e.creation))))))));
		return { title: b.name, el };
	}
	async function review(booking) {
		const v = await MP.prompt("Review this supplier", [{ name: "rating", label: "Overall (1–5)", type: "select", options: ["5", "4", "3", "2", "1"], reqd: 1 }, { name: "quality_rating", label: "Equipment quality", type: "select", options: ["", "5", "4", "3", "2", "1"] },
			{ name: "delivery_rating", label: "Delivery", type: "select", options: ["", "5", "4", "3", "2", "1"] }, { name: "communication_rating", label: "Communication", type: "select", options: ["", "5", "4", "3", "2", "1"] },
			{ name: "title", label: "Title", full: 1 }, { name: "comment", label: "Comment", type: "textarea", full: 1 }], "Submit review");
		if (v) { await MP.safe(() => C("review_submit", { booking, data: v }), "Thanks — published after moderation"); MP.reload(); }
	}
	async function dispute(booking) {
		const v = await MP.prompt("Raise a dispute", [{ name: "dispute_type", label: "Type", type: "select", options: ["Damage", "Loss", "Delivery", "Quality", "Billing", "Refund", "Cancellation", "Other"] }, { name: "claimed_amount", label: "Amount claimed", type: "number" },
			{ name: "description", label: "What happened?", type: "textarea", full: 1, reqd: 1 }], "Submit");
		if (v) { await MP.safe(() => C("dispute_raise", { booking, data: v }), "Dispute raised — the marketplace team will review"); MP.reload(); }
	}
	async function payment({ name }, q) {
		const p = await C("payment_get", { name });
		actions(p.booking ? link(`${BASE}/bookings/${encodeURIComponent(p.booking)}`, "Back to booking", "btn ghost sm") : "");
		const el = h("div", { class: "card stack", style: { maxWidth: "640px" } }, h("div", { class: "row between" }, h("h2", { style: { margin: 0 } }, MP.money(p.amount, p.currency)), h("span", { html: MP.badge(p.status) })),
			h("dl", { class: "dl" }, h("dt", {}, "Reference"), h("dd", {}, p.name), h("dt", {}, "For"), h("dd", {}, `${p.payment_type} · ${p.booking || ""}`), h("dt", {}, "Method"), h("dd", {}, p.gateway)));
		if (q.get("result") === "success") el.append(h("div", { class: "card flat", style: { background: "var(--green-soft)" } }, "Thanks — we are waiting for the payment provider's confirmation. This page updates once it arrives."));
		if (p.gateway === "Manual" && ["Pending", "Initiated"].includes(p.status)) {
			el.append(h("p", {}, p.instructions), h("form", { class: "row", onsubmit: async (e) => { e.preventDefault(); await MP.safe(() => C("payment_reference", { name, reference: e.target.ref.value }), "Reference submitted — Finance will confirm"); MP.reload(); } },
				h("input", { name: "ref", placeholder: "Your bank transfer reference", value: p.payer_reference || "", style: { flex: 1 }, required: true }), h("button", { class: "btn" }, "Submit reference")));
		} else if (p.checkout_url && ["Pending", "Initiated"].includes(p.status) && /^https?:/.test(p.checkout_url)) el.append(h("a", { class: "btn amber", href: p.checkout_url }, "Pay securely"));
		return { title: "Payment " + p.name, el };
	}

	// ---------------------------------------------------------------- sites & profile
	async function sites() {
		const rows = await C("sites");
		const edit = async (s = {}) => { const v = await MP.prompt(s.name ? "Edit site" : "New project site", [{ name: "project_name", label: "Project", reqd: 1, value: s.project_name }, { name: "city", label: "City", reqd: 1, value: s.city },
			{ name: "site_address", label: "Address", type: "textarea", full: 1, reqd: 1, value: s.site_address }, { name: "state", label: "State", value: s.state }, { name: "country", label: "Country", reqd: 1, value: s.country },
			{ name: "site_contact", label: "Site contact", value: s.site_contact }, { name: "site_phone", label: "Phone", value: s.site_phone }, { name: "site_access", label: "Accessibility", type: "textarea", full: 1, value: s.site_access }]);
			if (v) { await MP.safe(() => C("site_save", { data: v, name: s.name }), "Saved"); MP.reload(); } };
		actions(h("button", { class: "btn sm", onclick: () => edit() }, "Add site"));
		return { title: "Project sites", el: MP.table([{ label: "Project", key: "project_name" }, { label: "Address", key: "site_address" }, { label: "City", html: (s) => esc([s.city, s.country].join(", ")) }, { label: "Contact", key: "site_contact" }], rows, { onclick: edit, empty: "Save sites to reuse them in requirements." }) };
	}
	async function profile() {
		const p = await C("profile");
		const owner = p.role === "Owner";
		const form = MP.formFields([{ name: "customer_name", label: "Account name", value: p.customer_name, reqd: 1 }, { name: "customer_type", label: "Type", type: "select", options: ["Company", "Individual"], value: p.customer_type },
			{ name: "company_name", label: "Company name", value: p.company_name }, { name: "industry", label: "Industry", type: "select", options: ["", "Construction Company", "Civil Contractor", "Builder", "Infrastructure Developer", "Government Contractor", "Procurement Team", "Industrial Company", "Individual"], value: p.industry },
			{ name: "phone", label: "Phone", value: p.phone }, { name: "tax_id", label: "Tax / VAT number", value: p.tax_id }, { name: "country", label: "Country", value: p.country }, { name: "city", label: "City", value: p.city }]);
		actions(owner ? h("button", { class: "btn sm", onclick: async () => { await MP.safe(() => C("profile_update", { data: MP.readForm(form) }), "Saved"); } }, "Save") : "");
		return { title: "Company & users", el: h("div", { class: "stack" }, h("div", { class: "card" }, h("div", { class: "row between" }, h("h3", {}, "Company"), h("span", { html: MP.badge(p.status) + (p.verified ? ' <span class="badge green">Verified</span>' : "") })), form),
			h("div", { class: "card" }, h("div", { class: "row between" }, h("h3", {}, "Team members"), owner ? h("button", { class: "btn ghost sm", onclick: async () => { const v = await MP.prompt("Invite a colleague", [{ name: "email", label: "Email", type: "email", reqd: 1 }, { name: "full_name", label: "Name" }, { name: "member_role", label: "Role", type: "select", options: ["Buyer", "Viewer"] }], "Invite");
				if (v) { await MP.safe(() => C("member_add", v), "Invitation sent"); MP.reload(); } } }, "Invite") : ""),
				MP.table([{ label: "User", key: "user" }, { label: "Role", key: "member_role" }, { label: "Status", html: (m) => (m.enabled ? MP.badge("Active") : MP.badge("Disabled")) }], [{ user: p.owner_user, member_role: "Owner", enabled: 1 }, ...p.members]))) };
	}

	MP.portal({ base: BASE, routes: { "": overview, requests: requestsList, "requests/:name": requestDetail, "tenders/:name/compare": compare, bookings: bookingsList, "bookings/:name": bookingDetail,
		"payments/:name": payment, sites, profile } });
	C("notifications").then((n) => MP.setBell(n.unread)).catch(() => {});
})();
