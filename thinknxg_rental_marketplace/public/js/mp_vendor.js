/* Supplier portal: tenders & offers, catalogue & availability, bookings & fulfilment, finance, subscription, profile. */
(function () {
	const h = MP.h, esc = MP.esc, V = (m, a) => MP.call("vendor." + m, a), BASE = "/marketplace/vendor";
	const nav = [["", "home", "Dashboard", "^$"], ["tenders", "gavel", "Tenders & offers", "^tenders"], ["listings", "layers", "Equipment catalogue", "^listings"],
		["bookings", "truck", "Bookings & fulfilment", "^bookings"], ["finance", "money", "Billing & settlements", "^finance"], ["reviews", "star", "Reviews", "^reviews"],
		["subscription", "card", "Subscription", "^subscription"], ["profile", "shield", "Business profile", "^profile"]];
	MP.$("#side-nav").innerHTML = '<div class="sec">Workspace</div>' + nav.map(([p, i, l, m]) => `<a href="${BASE}/${p}" data-match="${m}">${MP.icon(i)}${l}</a>`).join("");
	MP.$(".bell").onclick = () => MP.notifPanel("vendor");
	const actions = (...els) => { const b = MP.$("#bar-actions"); b.innerHTML = ""; els.filter(Boolean).forEach((e) => b.append(e)); };
	const link = (href, label, cls = "btn sm") => h("a", { class: cls, href }, label);
	let ME = null;

	async function dashboard() {
		let d;
		try { d = await V("dashboard"); } catch (e) { if (e.code === "NOT_A_VENDOR") { location.href = "/marketplace/for-suppliers#register"; } throw e; }
		ME = d; MP.setBell(d.notifications.unread);
		const v = d.vendor, c = d.counts, ent = d.entitlements;
		actions(link(BASE + "/tenders", "Open tenders", "btn amber sm"), link(BASE + "/listings/new", "Add equipment", "btn ghost sm"));
		const el = h("div", { class: "stack" });
		if (v.status !== "Approved") el.append(h("div", { class: "card", style: { background: "var(--amber-soft)", borderColor: "#f3d18f" } }, h("h3", {}, "Account status: " + v.status),
			h("p", {}, { Draft: "Complete your profile and submit it for review.", "Documents Pending": "Upload your commercial registration and other verification documents.", "Under Review": "The marketplace team is reviewing your documents. You can prepare listings meanwhile.",
				Submitted: "Your application was received.", Rejected: "Your application was not approved: " + (v.status_reason || "") + ". Update your profile and resubmit.", Suspended: "Your account is suspended: " + (v.status_reason || "") }[v.status] || ""),
			link(BASE + "/profile", "Go to business profile")));
		el.append(MP.kpis([{ label: "Invited tenders open", value: c.invited_open, href: BASE + "/tenders" }, { label: "Offers submitted", value: c.submitted, href: BASE + "/tenders?scope=submitted" },
			{ label: "Winning offers", value: c.won, href: BASE + "/tenders?scope=won" }, { label: "Pending clarifications", value: c.open_clarifications, href: BASE + "/tenders" }]));
		el.append(MP.kpis([{ label: "Active bookings", value: c.active_bookings, href: BASE + "/bookings" }, { label: "Equipment at site", value: c.at_site, href: BASE + "/bookings" },
			{ label: "Returns due (7 days)", value: c.returns_due, href: BASE + "/bookings" }, { label: "Sale orders · contracts", value: `${c.sale_orders} · ${c.contracts}`, href: BASE + "/bookings" }]));
		el.append(h("div", { class: "grid g2" },
			h("div", { class: "card" }, h("h3", {}, "Revenue (confirmed bookings)"), d.revenue.length ? MP.table([{ label: "Currency", key: "currency" }, { label: "Booked value", html: (r) => MP.money(r.total, r.currency), right: 1 }, { label: "Platform commission", html: (r) => MP.money(r.commission, r.currency), right: 1 }], d.revenue) : h("p", { class: "muted" }, "No confirmed bookings yet.")),
			h("div", { class: "card" }, h("h3", {}, "Subscription"), ent.plan ? h("dl", { class: "dl" }, h("dt", {}, "Plan"), h("dd", {}, `${ent.plan_name} (${ent.status})`), h("dt", {}, "Renews / ends"), h("dd", {}, MP.date(ent.end_date)),
				h("dt", {}, "Listings"), h("dd", {}, `${c.listings} / ${ent.max_listings || "∞"}`), h("dt", {}, "Tender responses"), h("dd", {}, `${ent.max_tender_responses || "∞"} per month`)) : h("p", {}, ent.active ? "No plan required." : "No active subscription — you cannot publish or bid."), link(BASE + "/subscription", "Manage plan", "btn ghost sm"))));
		return { title: "Dashboard", el };
	}

	// ---------------------------------------------------------------- tenders
	async function tenders(p, q) {
		const scope = q.get("scope") || "invited";
		const res = await V("tenders_list", { scope });
		actions();
		const tabs = [["invited", "Invited"], ["open", "Open marketplace"], ["submitted", "My offers"], ["won", "Won"]];
		return { title: "Tenders & offers", el: h("div", {}, h("div", { class: "tabs" }, tabs.map(([k, l]) => h("a", { href: `${BASE}/tenders?scope=${k}`, class: k === scope ? "on" : "" }, l))),
			MP.table([{ label: "Tender", html: (t) => `<a href="${BASE}/tenders/${esc(t.name)}"><b>${esc(t.title)}</b></a><div class="small muted">${esc(t.name)} · ${esc(t.category)} · ${esc(t.lines)} line(s)</div>` },
				{ label: "Type", html: (t) => `<span class="badge navy">${esc(t.transaction_type)}</span> <span class="tiny muted">${esc(t.tender_type)}</span>` }, { label: "Location", html: (t) => esc([t.city, t.country].filter(Boolean).join(", ")) },
				{ label: "Deadline", html: (t) => `${MP.dt(t.submission_deadline)}<div class="tiny muted">${t.status === "Bidding Open" ? MP.until(t.submission_deadline) : esc(t.status)}</div>` },
				{ label: "Match", html: (t) => (t.match_score ? `<b>${Math.round(t.match_score)}</b>` : "—") },
				{ label: "My offer", html: (t) => (t.offer ? `${MP.badge(t.offer.status)}<div class="tiny">${MP.money(t.offer.grand_total, t.currency)} · rev ${t.offer.revision_no}</div>` : MP.badge(t.invitation_status || "Open")) }],
				res.rows, { onclick: (t) => MP.go(`${BASE}/tenders/${encodeURIComponent(t.name)}`), empty: scope === "open" ? "No open tenders match your categories and coverage right now." : "Nothing here yet." })) };
	}

	async function tender({ name }) {
		const t = await V("tender_get", { name }), cur = t.currency, el = h("div", { class: "stack" });
		const o = t.offer;
		actions(t.invitation_status && ["Invited", "Viewed"].includes(t.invitation_status) && !o ? h("button", { class: "btn ghost sm", onclick: async () => { await MP.safe(() => V("tender_respond", { name, response: "interested" }), "Marked as interested"); MP.reload(); } }, "Express interest") : null,
			t.invitation_status && !["Declined", "Offer Submitted"].includes(t.invitation_status) && !o ? h("button", { class: "btn ghost sm", onclick: async () => { const v = await MP.prompt("Decline tender", [{ name: "reason", label: "Reason (optional)", full: 1 }], "Decline"); if (v) { await MP.safe(() => V("tender_respond", { name, response: "decline", reason: v.reason }), "Declined"); MP.reload(); } } }, "Decline") : null,
			h("button", { class: "btn ghost sm", onclick: async () => { const v = await MP.prompt("Ask the customer", [{ name: "clarification_type", label: "Type", type: "select", options: ["Clarification", "Technical", "Commercial"] }, { name: "subject", label: "Subject", reqd: 1 }, { name: "message", label: "Question", type: "textarea", full: 1, reqd: 1 }], "Send");
				if (v) { await MP.safe(() => V("clarification_raise", { tender: name, ...v }), "Question sent"); MP.reload(); } } }, "Ask a question"));
		const period = t.transaction_type === "Hire" ? `${MP.date(t.required_from)} → ${MP.date(t.required_to)} · ${t.duration_days} days` : t.transaction_type === "Sale" ? `Deliver by ${MP.date(t.expected_delivery_date)}` : `${MP.date(t.contract_start)} · ${t.contract_months} months`;
		el.append(h("div", { class: "card" }, h("div", { class: "row between" }, h("div", {}, h("span", { class: "eyebrow" }, `${t.transaction_type} · ${t.tender_type} tender`), h("h2", { style: { margin: "4px 0" } }, t.title), h("span", { class: "muted" }, `${t.name} · ${t.category}`)),
			h("div", { class: "stack right" }, h("span", { html: MP.badge(t.status) }), h("b", {}, t.status === "Bidding Open" ? MP.until(t.submission_deadline) : "Deadline " + MP.dt(t.submission_deadline)))),
			h("div", { class: "grid g3", style: { marginTop: "14px" } }, h("div", {}, h("h4", {}, "Customer"), h("div", {}, t.customer.customer_name || t.customer.company_name), t.customer_disclosed ? h("div", { class: "small muted" }, [t.customer.email, t.customer.phone].filter(Boolean).join(" · ")) : h("div", { class: "tiny muted" }, "🔒 Identity disclosed on " + (t.disclosure_stage || "award").toLowerCase())),
				h("div", {}, h("h4", {}, "Site"), h("div", {}, t.site.site_address), t.site.site_contact ? h("div", { class: "small muted" }, t.site.site_contact + " · " + (t.site.site_phone || "")) : ""),
				h("div", {}, h("h4", {}, "Period"), h("div", {}, period)))));
		el.append(h("div", { class: "card" }, h("h3", {}, "Requirements"), MP.table([{ label: "Item", html: (i) => `<b>${esc(i.equipment_name)}</b><div class="small muted">${esc(i.specifications || "")}</div>` }, { label: "Qty", html: (i) => esc(i.qty + " " + i.uom), right: 1 },
			{ label: "Condition / brand", html: (i) => esc([i.condition_required, i.brand_preference].filter(Boolean).join(" · ") || "—") }, { label: "Certifications", key: "certifications_required" }, { label: "Alternatives", html: (i) => (i.accept_alternatives && t.allow_alternatives ? "Accepted" : "No") }], t.items),
			h("div", { class: "grid g2", style: { marginTop: "14px" } }, h("dl", { class: "dl small" }, ...Object.entries({ "Delivery required": t.requirements.delivery_required ? "Yes" : "No", "Transport": t.requirements.transport_required ? "Required" : "Not required", "Installation": t.requirements.installation_required ? "Required" : "No",
				"Technical support": t.requirements.technical_support ? "Required" : "No", "Payment terms wanted": t.requirements.payment_terms_pref || "—", "Special requirements": t.requirements.special_requirements || "—", "Other conditions": t.requirements.other_conditions || "—" }).flatMap(([k, v]) => [h("dt", {}, k), h("dd", {}, v)])),
				h("div", {}, h("h4", {}, "Documents"), t.attachments.length ? t.attachments.map((a) => h("div", {}, h("a", { href: MP.fileLink(a.file), target: "_blank" }, "📎 " + a.title))) : h("p", { class: "muted small" }, "None shared."),
					t.terms ? h("div", {}, h("h4", {}, "Terms"), h("p", { class: "small" }, t.terms)) : "", t.required_qualifications ? h("div", {}, h("h4", {}, "Qualifications"), h("p", { class: "small" }, t.required_qualifications)) : "",
					t.budget_max ? h("p", { class: "small" }, "Customer budget up to " + MP.money(t.budget_max, cur)) : "", t.current_lowest ? h("p", { class: "small" }, h("b", {}, "Reverse auction — current lowest: " + MP.money(t.current_lowest, cur))) : ""))));
		el.append(offerEditor(t));
		if (t.clarifications.length || t.my_clarifications.length) el.append(h("div", { class: "card" }, h("h3", {}, "Clarifications"), h("div", { class: "stack" }, [...t.my_clarifications, ...t.clarifications.map((c) => ({ ...c, shared: 1, status: "Answered" }))].map((c) =>
			h("div", { class: "card flat" }, h("div", { class: "row between" }, h("b", {}, c.subject), h("span", { html: MP.badge(c.status) + (c.shared ? ' <span class="badge">Shared with all</span>' : ` <span class="badge">${esc(c.clarification_type || "")}</span>`) })), h("p", { class: "small" }, c.message),
				c.counter_amount ? h("div", { class: "small" }, h("b", {}, "Customer counter-offer: " + MP.money(c.counter_amount, cur))) : "", c.response ? h("div", { class: "small", style: { background: "var(--steel-50)", padding: "8px", borderRadius: "8px" } }, h("b", {}, "Answer: "), c.response) : "",
				c.status === "Open" && c.raised_by_party === "Customer" && !["Counteroffer", "Revision Request"].includes(c.clarification_type) ? h("button", { class: "btn sm", onclick: async () => { const v = await MP.prompt("Reply", [{ name: "response", label: "Answer", type: "textarea", full: 1, reqd: 1 }], "Send"); if (v) { await MP.safe(() => V("clarification_respond", { name: c.name, response: v.response }), "Sent"); MP.reload(); } } }, "Reply") : "",
				c.status === "Open" && ["Counteroffer", "Revision Request"].includes(c.clarification_type) ? h("div", { class: "tiny muted" }, "Answer by submitting a revised offer below.") : "")))));
		return { title: t.name, el };
	}

	function offerEditor(t) {
		const cur = t.currency, o = t.offer || {}, box = h("div", { class: "card" });
		const editable = t.can_offer;
		const listingsFor = (ti) => t.my_listings;
		const rateFor = (l) => (t.transaction_type === "Sale" ? l.sale_price : t.transaction_type === "Contract" ? l.contract_monthly_rate : l.monthly_rate || l.weekly_rate || l.daily_rate) || 0;
		const basisFor = (l) => (t.transaction_type === "Sale" ? "Unit" : t.transaction_type === "Contract" ? "Monthly" : l && !l.monthly_rate && l.weekly_rate ? "Weekly" : l && !l.monthly_rate && !l.weekly_rate && l.daily_rate ? "Daily" : "Monthly");
		const lines = (o.items && o.items.length ? o.items : t.items.map((ti) => ({ tender_item: ti.name, equipment_name: ti.equipment_name, qty: ti.qty, uom: ti.uom, rate_basis: t.transaction_type === "Sale" ? "Unit" : "Monthly", unit_rate: "", compliance: "Compliant" }))).map((x) => ({ ...x }));
		const hdr = { delivery_date: o.delivery_date || t.required_from || t.contract_start || t.expected_delivery_date || "", valid_until: o.valid_until || new Date(Math.max(new Date(String(t.submission_deadline).replace(" ", "T")), Date.now()) + 14 * 864e5).toISOString().slice(0, 10), payment_terms: o.payment_terms || "", technical_compliance: o.technical_compliance || "Full",
			compliance_notes: o.compliance_notes || "", commercial_conditions: o.commercial_conditions || "", security_deposit: o.security_deposit || "", transport_charges: o.transport_charges || "", loading_charges: o.loading_charges || "",
			installation_charges: o.installation_charges || "", mobilization_charges: o.mobilization_charges || "", demobilization_charges: o.demobilization_charges || "", tax_percent: o.tax_percent ?? 5, availability_confirmed: o.availability_confirmed || 0 };
		const lineTable = h("div", { class: "stack" });
		const drawLines = () => { lineTable.innerHTML = ""; lines.forEach((ln, i) => {
			const ti = t.items.find((x) => x.name === ln.tender_item) || {};
			const ls = listingsFor(ti);
			const set = (k) => (e) => { ln[k] = e.target.type === "checkbox" ? (e.target.checked ? 1 : 0) : e.target.value; if (k === "listing") { const l = ls.find((x) => x.name === ln.listing); if (l) { ln.unit_rate = ln.unit_rate || rateFor(l); ln.rate_basis = basisFor(l); drawLines(); } } };
			const free = ls.find((x) => x.name === ln.listing)?.free_for_window;
			lineTable.append(h("div", { class: "item-row", style: { gridTemplateColumns: "1.6fr 1.6fr .6fr .8fr .8fr auto" } },
				h("label", { class: "field" }, h("span", {}, "For requirement"), h("select", { onchange: set("tender_item"), disabled: !editable || null }, t.items.map((x) => h("option", { value: x.name, selected: x.name === ln.tender_item || null }, `${x.equipment_name} (${x.qty} ${x.uom})`)))),
				h("label", { class: "field" }, h("span", {}, "From your listing"), h("select", { onchange: set("listing"), disabled: !editable || null }, h("option", { value: "" }, t.transaction_type === "Sale" ? "— not listed —" : "— choose (required) —"), ls.map((l) => h("option", { value: l.name, selected: l.name === ln.listing || null }, `${l.title} · ${Math.floor(l.free_for_window)} free`))),
					free !== undefined ? h("small", { class: free >= Number(ln.qty) ? "verified" : "muted", style: { color: free >= Number(ln.qty) ? "" : "var(--red)" } }, `${Math.floor(free)} free for the requested dates`) : ""),
				h("label", { class: "field" }, h("span", {}, "Qty"), h("input", { type: "number", step: "any", value: ln.qty, oninput: set("qty"), disabled: !editable || null })),
				h("label", { class: "field" }, h("span", {}, "Rate basis"), t.transaction_type === "Sale" ? h("input", { value: "Per unit", disabled: true }) : h("select", { onchange: set("rate_basis"), disabled: !editable || null }, ["Daily", "Weekly", "Monthly"].map((b) => h("option", { selected: (ln.rate_basis || "Monthly") === b || null }, b)))),
				h("label", { class: "field" }, h("span", {}, `Rate (${cur})`), h("input", { type: "number", step: "any", min: 0, value: ln.unit_rate, oninput: set("unit_rate"), disabled: !editable || null })),
				editable && lines.length > 1 ? h("button", { class: "btn ghost sm", onclick: () => { lines.splice(i, 1); drawLines(); } }, "✕") : h("span"),
				h("label", { class: "field" }, h("span", {}, "Compliance"), h("select", { onchange: set("compliance"), disabled: !editable || null }, ["Compliant", "Partial", "Non-Compliant"].map((c) => h("option", { selected: ln.compliance === c || null }, c)))),
				t.allow_alternatives && ti.accept_alternatives ? h("label", { class: "check" }, h("input", { type: "checkbox", checked: ln.is_alternative ? true : null, onchange: set("is_alternative"), disabled: !editable || null }), "Alternative equipment") : h("span"),
				h("label", { class: "field", style: { gridColumn: "span 3" } }, h("span", {}, "Remarks / alternative details"), h("input", { value: ln.alternative_details || ln.remarks || "", oninput: (e) => { ln.remarks = e.target.value; ln.alternative_details = ln.is_alternative ? e.target.value : ""; }, disabled: !editable || null })),
				ln.amount !== undefined ? h("div", { class: "right" }, h("span", { class: "tiny muted" }, `× ${ln.periods} periods`), h("div", {}, h("b", {}, MP.money(ln.amount, cur)))) : h("span")));
		}); };
		drawLines();
		const fieldsBox = MP.formFields([{ name: "delivery_date", label: "Delivery / mobilisation date", type: "date", reqd: 1, value: hdr.delivery_date }, { name: "valid_until", label: "Offer valid until", type: "date", reqd: 1, value: hdr.valid_until },
			{ name: "payment_terms", label: "Payment terms", value: hdr.payment_terms }, { name: "technical_compliance", label: "Technical compliance", type: "select", options: ["Full", "Partial", "Alternative"], value: hdr.technical_compliance },
			{ name: "security_deposit", label: "Security deposit (refundable)", type: "number", value: hdr.security_deposit }, { name: "transport_charges", label: "Transport", type: "number", value: hdr.transport_charges },
			{ name: "loading_charges", label: "Loading / unloading", type: "number", value: hdr.loading_charges }, { name: "installation_charges", label: "Installation", type: "number", value: hdr.installation_charges },
			...(t.transaction_type === "Contract" ? [{ name: "mobilization_charges", label: "Mobilisation", type: "number", value: hdr.mobilization_charges }, { name: "demobilization_charges", label: "Demobilisation", type: "number", value: hdr.demobilization_charges }] : []),
			{ name: "tax_percent", label: "Tax %", type: "number", value: hdr.tax_percent }, { name: "compliance_notes", label: "Compliance notes", type: "textarea", value: hdr.compliance_notes },
			{ name: "commercial_conditions", label: "Commercial conditions (damage, loss, extension terms…)", type: "textarea", full: 1, value: hdr.commercial_conditions },
			{ name: "availability_confirmed", label: "I confirm this equipment is available for the requested period", type: "check", full: 1, value: hdr.availability_confirmed }], "grid g3");
		if (!editable) MP.$$("input,select,textarea", fieldsBox).forEach((x) => (x.disabled = true));
		const totals = h("div", { class: "grid g4" });
		const showTotals = (x) => { totals.innerHTML = ""; [["Equipment", x.subtotal], ["Charges", x.charges_total], ["Tax", x.tax_amount], ["Offer total", x.grand_total]].forEach(([k, v], i) => totals.append(h("div", { class: "card kpi " + (i === 3 ? "accent" : "") }, h("span", {}, k), h("b", { style: { fontSize: "1.4rem" } }, MP.money(v, cur))))); };
		if (o.grand_total !== undefined) showTotals(o);
		const payload = () => ({ ...MP.readForm(fieldsBox), items: lines.map((l) => ({ tender_item: l.tender_item, equipment_name: (t.items.find((x) => x.name === l.tender_item) || {}).equipment_name, listing: l.listing || null, qty: Number(l.qty), uom: l.uom, rate_basis: l.rate_basis, unit_rate: Number(l.unit_rate), compliance: l.compliance, is_alternative: l.is_alternative || 0, alternative_details: l.alternative_details, remarks: l.remarks })) });
		const saveDraft = async () => { const r = await V("offer_save", { tender: t.name, data: payload() }); r.items.forEach((it, i) => Object.assign(lines[i] || {}, it)); drawLines(); showTotals(r); return r; };
		box.append(h("div", { class: "row between" }, h("h3", { style: { margin: 0 } }, o.name ? `Your offer · revision ${o.revision_no}` : "Prepare your offer"), o.status ? h("span", { html: MP.badge(o.status) + (o.rank ? ` <span class="badge blue">Rank ${o.rank}${o.rank_of ? " of " + o.rank_of : ""}</span>` : "") }) : ""),
			h("p", { class: "small muted" }, "Totals are calculated by the marketplace with the same rules for every supplier. Competitors never see your prices."),
			lineTable, editable ? h("button", { class: "btn ghost sm", onclick: () => { lines.push({ tender_item: t.items[0].name, qty: t.items[0].qty, uom: t.items[0].uom, unit_rate: "", rate_basis: t.transaction_type === "Sale" ? "Unit" : "Monthly", compliance: "Compliant" }); drawLines(); } }, "+ Add line") : "",
			h("div", { style: { marginTop: "16px" } }, fieldsBox), h("div", { style: { marginTop: "16px" } }, totals));
		if (editable) box.append(h("div", { class: "row", style: { marginTop: "18px" } },
			h("button", { class: "btn ghost", onclick: () => MP.safe(saveDraft, "Draft saved — totals recalculated") }, "Save draft & calculate"),
			h("button", { class: "btn amber", onclick: async () => {
				const reason = o.revision_no ? (await MP.prompt("Revised offer", [{ name: "reason", label: "What changed?", full: 1 }], "Submit revision") || {}).reason : null;
				if (o.revision_no && reason === undefined) return;
				await MP.safe(async () => { const d = await saveDraft(); await V("offer_submit", { offer: d.name, reason, idempotency_key: MP.uuid() }); }, o.revision_no ? "Revised offer submitted" : "Offer submitted"); MP.reload(); } }, o.revision_no ? "Submit revised offer" : "Submit offer"),
			o.name && o.status !== "Draft" ? h("button", { class: "btn ghost", onclick: async () => { const v = await MP.prompt("Withdraw offer", [{ name: "reason", label: "Reason", full: 1 }], "Withdraw"); if (v) { await MP.safe(() => V("offer_withdraw", { offer: o.name, reason: v.reason }), "Offer withdrawn"); MP.reload(); } } }, "Withdraw") : ""));
		else box.append(h("p", { class: "small muted", style: { marginTop: "14px" } }, o.status === "Accepted" ? "🎉 Your offer was accepted — see Bookings." : t.status === "Bidding Open" ? "" : "This tender is no longer accepting offers."));
		if (o.revisions && o.revisions.length) box.append(h("details", { style: { marginTop: "14px" } }, h("summary", { class: "small", style: { cursor: "pointer" } }, `Revision history (${o.revisions.length})`),
			MP.table([{ label: "Rev", key: "revision_no" }, { label: "Total", html: (r) => MP.money(r.grand_total, cur), right: 1 }, { label: "Submitted", html: (r) => MP.dt(r.submitted_on) }, { label: "Reason", key: "reason" }], o.revisions)));
		if (!t.my_listings.length) box.prepend(h("div", { class: "card flat small", style: { background: "var(--amber-soft)", marginBottom: "12px" } }, "You have no published listings for this offering type. Publish equipment in your catalogue to reserve stock against an award. ", link(BASE + "/listings/new", "Add equipment", "btn sm")));
		return box;
	}

	// ---------------------------------------------------------------- catalogue
	async function listings(p, q) {
		const res = await V("listings_list", { status: q.get("status") || "", q: q.get("q") || "" });
		actions(link(BASE + "/listings/new", "Add equipment", "btn amber sm"));
		return { title: "Equipment catalogue", el: MP.table([{ label: "Listing", html: (l) => `<div class="row"><div class="avatar" style="width:44px;height:44px;${l.cover_image ? `background-image:url('${esc(l.cover_image)}')` : ""}">${l.cover_image ? "" : "⛭"}</div><div><b>${esc(l.title)}</b><div class="small muted">${esc(l.category)}</div></div></div>` },
			{ label: "Offered for", html: (l) => [l.allow_hire && "Hire", l.allow_sale && "Sale", l.allow_contract && "Contract"].filter(Boolean).map((x) => `<span class="badge">${x}</span>`).join(" ") },
			{ label: "Qty (free today)", html: (l) => `${MP.num(l.total_qty)} <span class="muted">(${MP.num(l.available_today)})</span>`, right: 1 }, { label: "Rate", html: (l) => (l.monthly_rate ? MP.money(l.monthly_rate, l.currency) + "/mo" : l.sale_price ? MP.money(l.sale_price, l.currency) : "—"), right: 1 },
			{ label: "Status", html: (l) => MP.badge(l.status) + (l.featured ? ' <span class="badge green">Featured</span>' : "") }], res.rows, { onclick: (l) => MP.go(`${BASE}/listings/${encodeURIComponent(l.name)}`), empty: "No equipment yet — add your first listing." }) };
	}
	async function listingEdit({ name }) {
		const isNew = !name || name === "new";
		const [l, info] = await Promise.all([isNew ? Promise.resolve({ allow_hire: 1, currency: MP.currency, uom: "Nos", condition: "Used - Good", min_hire_days: 1, min_order_qty: 1, delivery_available: 1, specifications: [], images: [], availability: [] }) : V("listing_get", { name }), MP.call("public.site_info")]);
		const cats = info.categories.filter((c) => !c.is_group);
		const form = MP.formFields([{ name: "title", label: "Title", reqd: 1, value: l.title, full: 1 }, { name: "category", label: "Category", type: "select", options: cats.map((c) => [c.name, c.category_name]), value: l.category, reqd: 1 },
			{ name: "condition", label: "Condition", type: "select", options: ["New", "Used - Excellent", "Used - Good", "Refurbished"], value: l.condition }, { name: "brand", label: "Brand", value: l.brand }, { name: "model", label: "Model", value: l.model },
			{ name: "uom", label: "Unit", value: l.uom, reqd: 1 }, { name: "total_qty", label: "Total quantity in fleet", type: "number", value: l.total_qty, reqd: 1 }, { name: "currency", label: "Currency", value: l.currency }, { name: "manufacture_year", label: "Manufacture year", type: "number", value: l.manufacture_year },
			{ name: "allow_hire", label: "Offer for hire", type: "check", value: l.allow_hire }, { name: "allow_sale", label: "Offer for sale", type: "check", value: l.allow_sale }, { name: "allow_contract", label: "Offer on long-term contract", type: "check", value: l.allow_contract },
			{ name: "daily_rate", label: "Daily rate", type: "number", value: l.daily_rate }, { name: "weekly_rate", label: "Weekly rate", type: "number", value: l.weekly_rate }, { name: "monthly_rate", label: "Monthly rate", type: "number", value: l.monthly_rate },
			{ name: "min_hire_days", label: "Minimum hire (days)", type: "number", value: l.min_hire_days }, { name: "security_deposit_rate", label: "Security deposit per unit", type: "number", value: l.security_deposit_rate }, { name: "sale_price", label: "Sale price per unit", type: "number", value: l.sale_price },
			{ name: "min_order_qty", label: "Minimum order quantity", type: "number", value: l.min_order_qty }, { name: "contract_monthly_rate", label: "Contract monthly rate", type: "number", value: l.contract_monthly_rate }, { name: "min_contract_months", label: "Minimum contract months", type: "number", value: l.min_contract_months },
			{ name: "weight_per_unit_kg", label: "Weight per unit (kg)", type: "number", value: l.weight_per_unit_kg }, { name: "delivery_available", label: "Delivery available", type: "check", value: l.delivery_available }, { name: "installation_available", label: "Installation available", type: "check", value: l.installation_available },
			{ name: "short_description", label: "Short description", type: "textarea", full: 1, value: l.short_description }, { name: "description", label: "Full description", type: "textarea", full: 1, value: l.description },
			{ name: "certifications", label: "Certifications", type: "textarea", value: l.certifications }, { name: "warranty", label: "Warranty (sale)", type: "textarea", value: l.warranty }], "grid g3");
		const specs = (l.specifications || []).map((s) => ({ ...s })), images = (l.images || []).map((i) => ({ ...i }));
		let cover = l.cover_image || "", datasheet = l.datasheet || "";
		const specBox = h("div", { class: "stack" }), imgBox = h("div", { class: "row" });
		const drawSpecs = () => { specBox.innerHTML = ""; specs.forEach((s, i) => specBox.append(h("div", { class: "row" }, ...["attribute", "value", "unit"].map((k) => h("input", { placeholder: k, value: s[k] || "", style: { flex: k === "unit" ? ".5" : "1" }, oninput: (e) => (s[k] = e.target.value) })),
			h("button", { class: "btn ghost sm", onclick: () => { specs.splice(i, 1); drawSpecs(); } }, "✕")))); };
		const drawImgs = () => { imgBox.innerHTML = ""; [cover, ...images.map((i) => i.image)].filter(Boolean).forEach((src, i) => imgBox.append(h("div", { class: "avatar", style: { width: "96px", height: "72px", backgroundImage: `url('${src}')`, position: "relative" } },
			i === 0 ? h("span", { class: "badge navy", style: { position: "absolute", bottom: "4px", left: "4px" } }, "Cover") : h("button", { class: "btn ghost sm", style: { position: "absolute", top: "2px", right: "2px", padding: "2px 6px" }, onclick: () => { images.splice(i - 1, 1); drawImgs(); } }, "✕")))); };
		drawSpecs(); drawImgs();
		const pick = (accept, cb, pub) => { const inp = h("input", { type: "file", accept, multiple: !!pub, style: { display: "none" }, onchange: async (e) => { for (const f of e.target.files) { try { cb(await MP.upload(f, pub)); } catch (err) { MP.toast(err.message, "err"); } } } }); document.body.append(inp); inp.click(); };
		const save = async () => { const d = { ...MP.readForm(form), specifications: specs, images, cover_image: cover, datasheet }; const n = await MP.safe(() => V("listing_save", { data: d, name: isNew ? undefined : name }), "Saved"); if (isNew) MP.go(`${BASE}/listings/${encodeURIComponent(n)}`); else MP.reload(); };
		actions(h("button", { class: "btn sm", onclick: save }, "Save"), !isNew && l.status !== "Published" ? h("button", { class: "btn amber sm", onclick: async () => { await MP.safe(() => V("listing_status", { name, status: "Published" }), "Published"); MP.reload(); } }, "Publish") : null,
			!isNew && l.status === "Published" ? h("button", { class: "btn ghost sm", onclick: async () => { await MP.safe(() => V("listing_status", { name, status: "Paused" }), "Paused"); MP.reload(); } }, "Deactivate") : null,
			!isNew && l.route && l.status === "Published" ? h("a", { class: "btn ghost sm", href: "/marketplace/equipment/" + l.route, target: "_blank" }, "View public page") : null);
		const el = h("div", { class: "stack" }, !isNew ? h("div", { class: "row" }, h("span", { html: MP.badge(l.status) }), h("span", { class: "muted small" }, `${MP.num(l.available_today)} of ${MP.num(l.total_qty)} free today`)) : "",
			h("div", { class: "card" }, h("h3", {}, "Details & pricing"), form),
			h("div", { class: "grid g2" }, h("div", { class: "card" }, h("div", { class: "row between" }, h("h3", {}, "Images"), h("div", { class: "row" }, h("button", { class: "btn ghost sm", onclick: () => pick("image/*", (r) => { if (!cover) cover = r.file_url; else images.push({ image: r.file_url }); drawImgs(); }, 1) }, "Upload images"))), imgBox,
				h("h4", { style: { marginTop: "16px" } }, "Technical datasheet"), h("div", { class: "row" }, datasheet ? h("a", { href: MP.fileLink(datasheet), target: "_blank" }, "📄 Current datasheet") : h("span", { class: "muted small" }, "None"), h("button", { class: "btn ghost sm", onclick: () => pick(".pdf,.doc,.docx,.xls,.xlsx", (r) => { datasheet = r.file_url; MP.toast("Datasheet attached — save to keep it", "ok"); }, 0) }, "Upload PDF"))),
				h("div", { class: "card" }, h("div", { class: "row between" }, h("h3", {}, "Specifications"), h("button", { class: "btn ghost sm", onclick: () => { specs.push({}); drawSpecs(); } }, "+ Add")), specBox)));
		if (!isNew) {
			el.append(h("div", { class: "card" }, h("div", { class: "row between" }, h("h3", {}, "Availability & allocations"), h("button", { class: "btn ghost sm", onclick: async () => {
				const v = await MP.prompt("Block quantity", [{ name: "from_date", label: "From", type: "date", reqd: 1 }, { name: "to_date", label: "To", type: "date", reqd: 1 }, { name: "qty", label: "Quantity", type: "number", reqd: 1 }, { name: "entry_type", label: "Reason", type: "select", options: ["Blocked", "Maintenance"] }, { name: "remarks", label: "Remarks", full: 1 }], "Block");
				if (v) { await MP.safe(() => V("availability_block", { listing: name, ...v }), "Blocked"); MP.reload(); } } }, "Block dates")),
				h("p", { class: "small muted" }, "Bookings allocate quantity automatically and release it on return. Blocks stop the units being offered to new tenders."),
				MP.table([{ label: "Type", html: (a) => MP.badge(a.entry_type) }, { label: "From", html: (a) => MP.date(a.from_date) }, { label: "To", html: (a) => (a.to_date >= "2099" ? "Sold" : MP.date(a.to_date)) }, { label: "Qty", key: "qty", right: 1 },
					{ label: "Booking", html: (a) => (a.booking ? `<a href="${BASE}/bookings/${esc(a.booking)}">${esc(a.booking)}</a>` : esc(a.remarks || "")) },
					{ label: "", html: (a) => (a.booking ? "" : `<button class="btn ghost sm" data-rel="${esc(a.name)}">Release</button>`) }], l.availability, { empty: "Nothing allocated or blocked." })));
			el.addEventListener("click", async (e) => { const b = e.target.closest("[data-rel]"); if (b) { await MP.safe(() => V("availability_release", { name: b.dataset.rel }), "Released"); MP.reload(); } });
		}
		return { title: isNew ? "New listing" : l.title, el };
	}

	// ---------------------------------------------------------------- bookings
	async function bookings(p, q) {
		const tt = q.get("type") || "";
		const res = await V("bookings_list", { transaction_type: tt, status: q.get("status") || "" });
		actions();
		return { title: "Bookings & fulfilment", el: h("div", {}, h("div", { class: "tabs" }, [["", "All"], ["Hire", "Hire"], ["Sale", "Sale orders"], ["Contract", "Contracts"]].map(([k, l]) => h("a", { href: `${BASE}/bookings${k ? "?type=" + k : ""}`, class: k === tt ? "on" : "" }, l))),
			MP.table([{ label: "Booking", html: (b) => `<a href="${BASE}/bookings/${esc(b.name)}"><b>${esc(b.name)}</b></a><div class="small muted">${esc(b.project_name || "")} · ${esc(b.city || "")}</div>` }, { label: "Type", key: "transaction_type" },
				{ label: "Period", html: (b) => (b.transaction_type === "Sale" ? "Deliver " + MP.date(b.delivery_date) : `${MP.date(b.start_date)} → ${MP.date(b.end_date)}`) }, { label: "Status", html: (b) => MP.badge(b.status) },
				{ label: "Value", html: (b) => MP.money(b.grand_total, b.currency), right: 1 }, { label: "Paid", html: (b) => MP.money(b.amount_paid, b.currency), right: 1 }], res.rows, { onclick: (b) => MP.go(`${BASE}/bookings/${encodeURIComponent(b.name)}`), empty: "No bookings yet." })) };
	}
	async function booking({ name }) {
		const b = await V("booking_get", { name }), cur = b.currency, el = h("div", { class: "stack" });
		const LBL = { Dispatched: "Mark dispatched", "On Hire": "Confirm on hire", Delivered: "Mark delivered", Returned: "Record return", Mobilized: "Mark mobilised", Active: "Confirm active", Demobilized: "Mark demobilised", Completed: "Complete booking" };
		const doAct = async (a) => {
			let data = {};
			if (a === "Dispatched") { data = await MP.prompt("Dispatch", [{ name: "vehicle_details", label: "Vehicle / trip", reqd: 1 }, { name: "driver_contact", label: "Driver contact" }], "Mark dispatched"); if (!data) return; }
			else if (a === "Returned") {
				const box = h("div", { class: "stack" }, MP.table([{ label: "Item", key: "equipment_name" }, { label: "Hired", key: "qty", right: 1 },
					{ label: "Returned", html: (i) => `<input type="number" step="any" data-k="returned_qty" data-n="${esc(i.name)}" value="${i.qty}" style="width:90px">` }, { label: "of which damaged", html: (i) => `<input type="number" step="any" data-k="damaged_qty" data-n="${esc(i.name)}" value="0" style="width:90px">` },
					{ label: "Lost", html: (i) => `<input type="number" step="any" data-k="lost_qty" data-n="${esc(i.name)}" value="0" style="width:90px">` }], b.items),
					MP.formFields([{ name: "additional_charges", label: `Damage / loss / extra-day charges (${cur})`, type: "number", value: 0 }]));
				const ok = await MP.modal({ title: "Record return & final settlement", body: box, wide: true, actions: [{ label: "Cancel", class: "ghost", value: null }, { label: "Record return", handler: (m) => {
					const lines = {}; MP.$$("input[data-n]", m).forEach((i) => { (lines[i.dataset.n] = lines[i.dataset.n] || { name: i.dataset.n })[i.dataset.k] = Number(i.value); });
					return { lines: Object.values(lines), additional_charges: Number(MP.$("input[name=additional_charges]", m).value || 0) }; } }] });
				if (!ok) return; data = ok;
			} else if (!(await MP.confirm(LBL[a] + "?", "The customer is notified.", LBL[a]))) return;
			await MP.safe(() => V("booking_action", { name, action: a, data }), "Updated"); MP.reload();
		};
		actions(...b.next_actions.map((a) => h("button", { class: "btn sm " + (a === "Completed" ? "green" : ""), onclick: () => doAct(a) }, LBL[a] || a)),
			b.can_cancel ? h("button", { class: "btn ghost sm", onclick: async () => { const v = await MP.prompt("Cancel booking", [{ name: "reason", label: "Reason", full: 1, reqd: 1 }], "Cancel booking"); if (v) { await MP.safe(() => V("booking_action", { name, action: "cancel", data: v }), "Cancelled — customer refunded"); MP.reload(); } } }, "Cancel") : null);
		el.append(h("div", { class: "card row between" }, h("div", {}, h("span", { class: "eyebrow" }, b.transaction_type), h("h2", { style: { margin: "4px 0" } }, b.name), h("span", { class: "muted" }, b.project_name || "")), h("div", { html: MP.badge(b.status) })));
		if (b.status === "Pending Payment") el.append(h("div", { class: "card small", style: { background: "var(--amber-soft)" } }, "Waiting for the customer's deposit. Your quantity is reserved; contact details are shared once it is paid."));
		b.extension_requests.forEach((x) => el.append(h("div", { class: "card row between", style: { background: "var(--blue-soft)" } }, h("b", {}, x.subject), h("button", { class: "btn sm", onclick: async () => {
			const v = await MP.prompt("Approve extension", [{ name: "new_end", label: "New end date", type: "date", reqd: 1, value: (x.subject.split("→ ")[1] || "").trim() }], "Approve & bill");
			if (v) { await MP.safe(() => V("booking_action", { name, action: "approve_extension", data: v }), "Extension approved — charge added to the schedule"); MP.reload(); } } }, "Approve"))));
		const vo = b.vendor_order || {}, ci = b.customer_info || {};
		el.append(h("div", { class: "grid g2" }, h("div", { class: "card" }, h("h3", {}, "Customer & site"), h("dl", { class: "dl" }, h("dt", {}, "Customer"), h("dd", {}, ci.company_name || ci.customer_name), ci.email ? [h("dt", {}, "Contact"), h("dd", {}, `${ci.email} · ${ci.phone || ""}`)] : "",
			h("dt", {}, "Site"), h("dd", {}, b.site_address || "—"), b.site ? [h("dt", {}, "Site contact"), h("dd", {}, `${b.site.site_contact || ""} ${b.site.site_phone || ""}`), h("dt", {}, "Access"), h("dd", {}, b.site.site_access || "—")] : "",
			h("dt", {}, "Period"), h("dd", {}, b.transaction_type === "Sale" ? "Deliver " + MP.date(b.delivery_date) : `${MP.date(b.start_date)} → ${MP.date(b.end_date)}`))),
			h("div", { class: "card" }, h("h3", {}, "Fulfilment"), h("dl", { class: "dl" }, h("dt", {}, "Order"), h("dd", {}, `${vo.name || ""} · ${vo.status || ""}`), h("dt", {}, "Mode"), h("dd", {}, vo.fulfilment_mode || "Marketplace"),
				vo.erp_reference ? [h("dt", {}, "ERP document"), h("dd", {}, h("a", { href: `/app/${vo.erp_reference_doctype.toLowerCase().replace(/ /g, "-")}/${encodeURIComponent(vo.erp_reference)}`, target: "_blank" }, `${vo.erp_reference_doctype} ${vo.erp_reference}`), h("div", { class: "tiny muted" }, vo.erp_status || ""))] : "",
				h("dt", {}, "Dispatched"), h("dd", {}, MP.dt(vo.dispatched_on)), h("dt", {}, "Delivered"), h("dd", {}, MP.dt(vo.delivered_on)), h("dt", {}, "Return due"), h("dd", {}, MP.date(vo.return_due)), h("dt", {}, "Returned"), h("dd", {}, MP.dt(vo.returned_on))))));
		el.append(h("div", { class: "card" }, h("h3", {}, "Items"), MP.table([{ label: "Item", key: "equipment_name" }, { label: "Qty", key: "qty", right: 1 }, { label: "Rate", html: (i) => `${MP.money(i.unit_rate, cur)} <span class="tiny muted">${esc(i.rate_basis)}</span>`, right: 1 },
			{ label: "Amount", html: (i) => MP.money(i.amount, cur), right: 1 }, { label: "Ret / dmg / lost", html: (i) => `${i.returned_qty || 0} / ${i.damaged_qty || 0} / ${i.lost_qty || 0}` }], b.items),
			h("div", { class: "grid g4", style: { marginTop: "14px" } }, [["Booking value", b.grand_total], ["Paid by customer", b.amount_paid], ["Balance due", b.balance_due], [`Commission (${b.commission_basis === "Percentage" ? b.commission_rate + "%" : "fixed"})`, b.commission_amount]].map(([k, v]) => h("div", { class: "card kpi" }, h("span", {}, k), h("b", { style: { fontSize: "1.3rem" } }, MP.money(v, cur)))))));
		el.append(h("div", { class: "card" }, h("h3", {}, "Billing schedule"), MP.table([{ label: "Line", key: "line_type" }, { label: "Due", html: (s) => MP.date(s.due_date) }, { label: "Status", html: (s) => MP.badge(s.status) }, { label: "Amount", html: (s) => MP.money(s.amount, cur), right: 1 }], b.schedule)));
		el.append(h("div", { class: "card" }, h("h3", {}, "Activity"), h("div", { class: "timeline" }, b.history.map((e) => h("div", {}, h("b", {}, e.event), e.to_state ? " → " + e.to_state : "", h("span", { class: "muted" }, " · " + MP.dt(e.creation)))))));
		return { title: b.name, el };
	}

	// ---------------------------------------------------------------- finance, subscription, reviews
	async function finance() {
		const f = await V("finance"); actions();
		return { title: "Billing & settlements", el: h("div", { class: "stack" },
			h("div", { class: "card" }, h("h3", {}, "Settlements"), h("p", { class: "small muted" }, "A settlement is marked paid only with a bank or provider payout reference."), MP.table([{ label: "Settlement", key: "name" }, { label: "Period", html: (s) => `${MP.date(s.period_from)} → ${MP.date(s.period_to)}` },
				{ label: "Gross", html: (s) => MP.money(s.gross_amount, s.currency), right: 1 }, { label: "Commission", html: (s) => MP.money(s.commission_amount, s.currency), right: 1 }, { label: "Refunds", html: (s) => MP.money(s.refund_amount, s.currency), right: 1 },
				{ label: "Net payable", html: (s) => `<b>${MP.money(s.net_payable, s.currency)}</b>`, right: 1 }, { label: "Status", html: (s) => MP.badge(s.status) + (s.payout_reference ? `<div class="tiny muted">ref ${esc(s.payout_reference)}</div>` : "") }], f.settlements, { empty: "No settlements yet." })),
			h("div", { class: "card" }, h("h3", {}, "Commission"), MP.table([{ label: "Booking", html: (c) => `<a href="${BASE}/bookings/${esc(c.booking)}">${esc(c.booking)}</a>` }, { label: "Basis", html: (c) => esc(c.basis === "Percentage" ? c.rate + "%" : "Fixed") },
				{ label: "On", html: (c) => MP.money(c.base_amount, c.currency), right: 1 }, { label: "Commission", html: (c) => MP.money(c.commission_amount, c.currency), right: 1 }, { label: "Status", html: (c) => MP.badge(c.status) }], f.commissions)),
			h("div", { class: "card" }, h("h3", {}, "Customer payments on your bookings"), MP.table([{ label: "Payment", key: "name" }, { label: "Booking", key: "booking" }, { label: "Type", key: "payment_type" }, { label: "Status", html: (p) => MP.badge(p.status) }, { label: "Amount", html: (p) => MP.money(p.amount, p.currency), right: 1 }, { label: "Confirmed", html: (p) => MP.dt(p.confirmed_on) }], f.payments))) };
	}
	async function subscription() {
		const s = await V("subscription"), e = s.entitlements; actions();
		const bar = (used, max) => h("div", {}, h("div", { class: "row between small" }, h("span", {}, `${used} / ${max || "∞"}`)), h("div", { class: "score-bar" }, h("i", { style: { width: max ? Math.min(used / max * 100, 100) + "%" : "8%" } })));
		return { title: "Subscription", el: h("div", { class: "stack" },
			h("div", { class: "card" }, h("div", { class: "row between" }, h("h3", {}, e.plan ? `${e.plan_name} plan` : "No active plan"), e.status ? h("span", { html: MP.badge(e.status) }) : ""), e.end_date ? h("p", { class: "muted" }, "Current period ends " + MP.date(e.end_date)) : "",
				h("div", { class: "grid g3" }, h("div", {}, h("h4", {}, "Published listings"), bar(s.usage.listings, e.max_listings)), h("div", {}, h("h4", {}, "Tender responses this month"), bar(s.usage.offers_this_month, e.max_tender_responses)), h("div", {}, h("h4", {}, "Team users"), bar(s.usage.staff, e.max_staff_users)))),
			h("div", { class: "grid g3" }, s.plans.map((p) => h("div", { class: "card" + (p.name === e.plan ? " short" : ""), style: p.name === e.plan ? { outline: "2px solid var(--amber)" } : null }, h("h3", {}, p.plan_name),
				h("div", { style: { font: "700 1.8rem var(--font-head)", color: "var(--navy)" } }, p.price_monthly ? MP.money(p.price_monthly, p.currency) + " /mo" : "Free"), p.price_yearly ? h("div", { class: "small muted" }, MP.money(p.price_yearly, p.currency) + " / year") : "",
				h("ul", { class: "small" }, h("li", {}, `${p.max_listings || "Unlimited"} listings`), h("li", {}, `${p.max_tender_responses || "Unlimited"} responses / month`), h("li", {}, `${p.max_staff_users || "Unlimited"} users`), p.advanced_reports ? h("li", {}, "Advanced reports") : "", p.api_access ? h("li", {}, "API access") : "", p.priority_support ? h("li", {}, "Priority support") : ""),
				h("div", { class: "row" }, ["Monthly", ...(p.price_yearly ? ["Yearly"] : [])].map((cy) => h("button", { class: "btn sm " + (cy === "Yearly" ? "ghost" : ""), onclick: async () => {
					if (!(await MP.confirm(`${p.name === e.plan ? "Renew" : "Switch to"} ${p.plan_name}?`, p.price_monthly ? "A payment is requested; the plan activates once it is received." : "Activates immediately.", "Continue"))) return;
					const r = await MP.safe(() => V("subscribe", { plan: p.name, cycle: cy })); if (r.checkout_url && /^https?:/.test(r.checkout_url)) location.href = r.checkout_url; else { MP.toast(r.status === "Active" ? "Plan active" : "Payment requested — Finance confirms bank transfers", "ok"); MP.reload(); } } }, p.name === e.plan ? "Renew " + cy.toLowerCase() : cy)))))),
			h("div", { class: "card" }, h("h3", {}, "Subscription history"), MP.table([{ label: "Plan", key: "plan" }, { label: "Change", key: "change_type" }, { label: "Period", html: (x) => `${MP.date(x.start_date)} → ${MP.date(x.end_date)}` }, { label: "Status", html: (x) => MP.badge(x.status) }, { label: "Amount", html: (x) => MP.money(x.amount, x.currency), right: 1 }], s.history)),
			h("div", { class: "card row between" }, h("div", {}, h("h3", {}, "Promote your business"), h("p", { class: "small muted" }, "Featured supplier placement on the homepage and directory, or featured listings in search.")),
				h("button", { class: "btn ghost", onclick: async () => { const v = await MP.prompt("Promotion", [{ name: "promotion_type", label: "Type", type: "select", options: ["Featured Supplier", "Featured Listing", "Premium Visibility"] }, { name: "days", label: "Days (min 7)", type: "number", value: 7 }, { name: "listing", label: "Listing ID (for featured listing)" }], "Request");
					if (v) { await MP.safe(() => V("promote", v), "Promotion requested — activates once paid"); } } }, "Request promotion"))) };
	}
	async function reviews() {
		const rows = await V("reviews"); actions();
		return { title: "Reviews", el: rows.length ? h("div", { class: "stack" }, rows.map((r) => h("div", { class: "card" }, h("div", { class: "row between" }, h("b", {}, r.title || r.booking), h("span", { class: "stars" }, MP.stars(r.rating * 5))), h("p", {}, r.comment || ""),
			h("div", { class: "small muted" }, `${r.reviewer_display_name} · ${MP.date(r.creation)} · quality ${MP.stars(r.quality_rating * 5)} · delivery ${MP.stars(r.delivery_rating * 5)}`),
			r.vendor_response ? h("div", { class: "small", style: { marginTop: "8px" } }, h("b", {}, "Your response: "), r.vendor_response) : h("button", { class: "btn ghost sm", style: { marginTop: "8px" }, onclick: async () => { const v = await MP.prompt("Respond publicly", [{ name: "response", label: "Response", type: "textarea", full: 1, reqd: 1 }], "Publish"); if (v) { await MP.safe(() => V("review_respond", { name: r.name, response: v.response }), "Published"); MP.reload(); } } }, "Respond"))))
			: h("div", { class: "empty" }, "Reviews appear after customers complete bookings and the marketplace publishes them.") };
	}

	// ---------------------------------------------------------------- profile
	async function profile() {
		const [p, info] = await Promise.all([V("profile"), MP.call("public.site_info")]);
		const owner = p.role === "Owner", mgr = owner || p.role === "Manager";
		const form = MP.formFields([{ name: "business_name", label: "Business name", value: p.business_name, reqd: 1 }, { name: "business_type", label: "Business type", type: "select", options: ["Scaffolding Rental", "Formwork Rental", "Equipment Rental", "Equipment Owner", "Industrial Supplier", "Material Dealer", "Manufacturer / Distributor", "Other"], value: p.business_type },
			{ name: "registration_number", label: "Registration number", value: p.registration_number, reqd: 1 }, { name: "tax_id", label: "Tax / VAT registration", value: p.tax_id }, { name: "years_in_business", label: "Years in business", type: "number", value: p.years_in_business },
			{ name: "website", label: "Website", value: p.website }, { name: "contact_person", label: "Contact person", value: p.contact_person, reqd: 1 }, { name: "email", label: "Email", value: p.email, reqd: 1 }, { name: "phone", label: "Phone", value: p.phone, reqd: 1 },
			{ name: "address_line1", label: "Address", value: p.address_line1, reqd: 1 }, { name: "address_line2", label: "Address line 2", value: p.address_line2 }, { name: "city", label: "City", value: p.city, reqd: 1 }, { name: "state", label: "State", value: p.state },
			{ name: "country", label: "Country", value: p.country, reqd: 1 }, { name: "pincode", label: "Postal code", value: p.pincode }, { name: "description", label: "Company description", type: "textarea", full: 1, value: p.description },
			...(owner ? [{ name: "bank_name", label: "Bank (settlements)", value: p.bank_name }, { name: "account_holder", label: "Account holder", value: p.account_holder }, { name: "iban", label: "IBAN / account", value: p.iban }, { name: "swift", label: "SWIFT / IFSC", value: p.swift }] : [])], "grid g3");
		let logo = p.logo || "";
		const cats = new Set(p.categories), locs = p.locations.map((l) => ({ ...l }));
		const catBox = h("div", { class: "row" }, info.categories.filter((c) => c.name !== "All Equipment").map((c) => h("label", { class: "check badge", style: { padding: "7px 11px", background: c.parent === "All Equipment" ? "var(--blue-soft)" : "" } },
			h("input", { type: "checkbox", checked: cats.has(c.name) || null, onchange: (e) => (e.target.checked ? cats.add(c.name) : cats.delete(c.name)) }), c.category_name)));
		const locBox = h("div", { class: "stack" });
		const drawLocs = () => { locBox.innerHTML = ""; locs.forEach((l, i) => locBox.append(h("div", { class: "row" }, ...[["city", 1], ["state", 1], ["country", 1], ["delivery_radius_km", 0.6]].map(([k, f]) => h("input", { placeholder: k.replace(/_/g, " "), value: l[k] ?? "", style: { flex: f }, oninput: (e) => (l[k] = e.target.value) })),
			h("button", { class: "btn ghost sm", onclick: () => { locs.splice(i, 1); drawLocs(); } }, "✕")))); };
		drawLocs();
		const save = async () => { await MP.safe(() => V("profile_update", { data: { ...MP.readForm(form), logo, categories: [...cats], locations: locs } }), "Profile saved"); MP.reload(); };
		actions(mgr ? h("button", { class: "btn sm", onclick: save }, "Save") : null, owner && ["Draft", "Rejected", "Documents Pending", "Submitted"].includes(p.status) ? h("button", { class: "btn amber sm", onclick: async () => { await save(); await MP.safe(() => V("submit_for_review"), "Submitted for review"); MP.reload(); } }, "Submit for review") : null);
		return { title: "Business profile", el: h("div", { class: "stack" },
			h("div", { class: "card row between" }, h("div", { class: "scard" }, h("div", { class: "avatar", id: "logo", style: logo ? { backgroundImage: `url('${logo}')` } : null }, logo ? "" : (p.business_name || "?")[0]),
				h("div", {}, h("h3", { style: { margin: 0 } }, p.business_name), h("span", { html: MP.badge(p.status) + (p.verified ? ' <span class="badge green">✔ Verified</span>' : "") }), p.status_reason ? h("div", { class: "small muted" }, p.status_reason) : "")),
				h("div", { class: "row" }, mgr ? h("button", { class: "btn ghost sm", onclick: () => { const inp = h("input", { type: "file", accept: "image/*", style: { display: "none" }, onchange: async (e) => { const r = await MP.safe(() => MP.upload(e.target.files[0], 1)); logo = r.file_url; MP.$("#logo").style.backgroundImage = `url('${logo}')`; MP.$("#logo").textContent = ""; } }); document.body.append(inp); inp.click(); } }, "Upload logo") : "",
					p.route && p.status === "Approved" ? h("a", { class: "btn ghost sm", href: "/marketplace/suppliers/" + p.route, target: "_blank" }, "Public profile") : "")),
			h("div", { class: "card" }, h("h3", {}, "Business details"), form),
			h("div", { class: "card" }, h("h3", {}, "Equipment categories"), h("p", { class: "small muted" }, "Tenders are matched on these categories, your service locations and the free stock in your published listings."), catBox),
			h("div", { class: "card" }, h("div", { class: "row between" }, h("h3", {}, "Operating & delivery locations"), h("button", { class: "btn ghost sm", onclick: () => { locs.push({ country: p.country }); drawLocs(); } }, "+ Add")), locBox),
			h("div", { class: "card" }, h("div", { class: "row between" }, h("h3", {}, "Verification documents"), mgr ? h("button", { class: "btn ghost sm", onclick: async () => {
				const v = await MP.prompt("Upload verification document", [{ name: "document_type", label: "Document", type: "select", options: ["Commercial Registration", "Tax Certificate", "Trade License", "Insurance Certificate", "Bank Letter", "ID of Signatory", "Equipment Certification", "Other"] }, { name: "document_number", label: "Number" }, { name: "expiry_date", label: "Expiry", type: "date" }], "Choose file");
				if (!v) return; const inp = h("input", { type: "file", style: { display: "none" }, onchange: async (e) => { const r = await MP.safe(() => MP.upload(e.target.files[0], 0)); await MP.safe(() => V("document_add", { ...v, file_url: r.file_url }), "Document uploaded"); MP.reload(); } }); document.body.append(inp); inp.click(); } }, "Upload document") : ""),
				MP.table([{ label: "Document", key: "document_type" }, { label: "Number", key: "document_number" }, { label: "Expiry", html: (d) => MP.date(d.expiry_date) }, { label: "Status", html: (d) => MP.badge(d.status) }, { label: "Remarks", key: "remarks" }], p.documents, { empty: "Upload your commercial registration to start verification." })),
			h("div", { class: "card" }, h("div", { class: "row between" }, h("h3", {}, "Team"), mgr ? h("button", { class: "btn ghost sm", onclick: async () => { const v = await MP.prompt("Add a team member", [{ name: "email", label: "Email", type: "email", reqd: 1 }, { name: "full_name", label: "Name" }, { name: "vendor_role", label: "Role", type: "select", options: owner ? ["Staff", "Manager", "Owner"] : ["Staff"] }], "Invite");
				if (v) { await MP.safe(() => V("staff_add", v), "Invitation sent"); MP.reload(); } } }, "Add user") : ""),
				MP.table([{ label: "User", html: (u) => `<b>${esc(u.full_name || "")}</b><div class="small muted">${esc(u.user)}</div>` }, { label: "Role", key: "vendor_role" }, { label: "Status", html: (u) => MP.badge(u.enabled ? "Active" : "Deactivated") },
					{ label: "", html: (u) => (mgr && u.vendor_role !== "Owner" ? `<button class="btn ghost sm" data-staff="${esc(u.name)}" data-en="${u.enabled ? 0 : 1}">${u.enabled ? "Disable" : "Enable"}</button>` : "") }], p.staff))) };
	}
	document.addEventListener("click", async (e) => { const b = e.target.closest("[data-staff]"); if (b) { await MP.safe(() => V("staff_toggle", { name: b.dataset.staff, enabled: b.dataset.en }), "Updated"); MP.reload(); } });

	MP.portal({ base: BASE, routes: { "": dashboard, tenders, "tenders/:name": tender, listings, "listings/new": () => listingEdit({}), "listings/:name": listingEdit, bookings, "bookings/:name": booking, finance, subscription, reviews, profile } });
	V("notifications").then((n) => MP.setBell(n.unread)).catch(() => {});
})();
