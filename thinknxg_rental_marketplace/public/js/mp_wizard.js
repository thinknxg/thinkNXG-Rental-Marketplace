/* Guided requirement wizard: 8 steps → Rental Request → Tender → matching. Totals and eligibility are decided server-side. */
(function () {
	const B = window.MP_BOOT, h = MP.h, esc = MP.esc;
	const KEY = "mp_requirement_draft";
	const STEPS = ["Transaction type", "Equipment category", "Requirements", "Period & delivery", "Project & site", "Commercial preferences", "Attachments", "Review & submit"];
	const store = { get() { try { return JSON.parse(localStorage.getItem(KEY) || "null"); } catch (e) { return null; } },
		set(v) { try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) {} }, clear() { try { localStorage.removeItem(KEY); } catch (e) {} } };
	const resume = new URLSearchParams(location.search).get("resume") && store.get();
	const pf = B.prefill || {};
	const S = resume || {
		step: pf.transaction_type ? 1 : 0, transaction_type: pf.transaction_type || "", category: pf.category || "", idempotency_key: MP.uuid(),
		items: [{ equipment_name: pf.q || "", qty: "", uom: "Nos", specifications: "", condition_required: "Any", brand_preference: "", accept_alternatives: 1, certifications_required: "", preferred_listing: pf.listing || "" }],
		city: pf.city || "", country: B.default_country || "", currency: B.currency, delivery_required: 1, transport_required: 1, attachments: [],
	};
	if (pf.category && !S.transaction_type) S.step = 0;
	const root = MP.$("#wizard");
	const cats = B.categories, byName = Object.fromEntries(cats.map((c) => [c.name, c]));
	const TODAY = new Date().toISOString().slice(0, 10);

	function save() { store.set(S); }
	function field(label, name, opts = {}) {
		const v = S[name] ?? "";
		let input;
		if (opts.type === "select") input = h("select", { name }, (opts.options || []).map((o) => h("option", { value: o, selected: String(v) === String(o) || null }, o || "—")));
		else if (opts.type === "textarea") input = h("textarea", { name, placeholder: opts.placeholder || "" }, v);
		else if (opts.type === "check") return h("label", { class: "check" }, h("input", { type: "checkbox", name, checked: S[name] ? true : null, onchange: (e) => { S[name] = e.target.checked ? 1 : 0; save(); } }), label);
		else input = h("input", { name, type: opts.type || "text", value: v, min: opts.min || null, placeholder: opts.placeholder || "", list: opts.list || null });
		input.addEventListener("input", (e) => { S[name] = e.target.type === "number" ? (e.target.value === "" ? "" : Number(e.target.value)) : e.target.value; save(); if (opts.onchange) opts.onchange(); });
		input.addEventListener("change", (e) => { S[name] = e.target.value; save(); if (opts.onchange) opts.onchange(); });
		return h("label", { class: "field", style: opts.full ? { gridColumn: "1/-1" } : null }, h("span", {}, label, opts.reqd ? h("em", {}, " *") : ""), input, opts.help ? h("small", { class: "muted" }, opts.help) : null);
	}
	const days = () => (S.required_from && S.required_to ? Math.round((new Date(S.required_to) - new Date(S.required_from)) / 864e5) + 1 : 0);

	function validate(step) {
		const e = [];
		if (step === 0 && !S.transaction_type) e.push("Choose Hire, Sale or Contract");
		if (step === 1) { if (!S.category) e.push("Choose a category"); else if (!byName[S.category]["allow_" + S.transaction_type.toLowerCase()]) e.push(`${S.transaction_type} is not offered for this category`); }
		if (step === 2) S.items.forEach((it, i) => { if (!it.equipment_name) e.push(`Line ${i + 1}: equipment name`); if (!(Number(it.qty) > 0)) e.push(`Line ${i + 1}: quantity`); if (!it.uom) e.push(`Line ${i + 1}: unit`); });
		if (step === 3) {
			if (S.transaction_type === "Hire") { if (!S.required_from || !S.required_to) e.push("Start and return dates"); else if (S.required_to < S.required_from) e.push("Return date is before start"); else if (S.required_from < TODAY) e.push("Start date is in the past"); }
			if (S.transaction_type === "Sale" && !S.expected_delivery_date) e.push("Expected delivery date");
			if (S.transaction_type === "Contract") { if (!S.contract_start) e.push("Contract start"); if (!(Number(S.contract_months) >= 1)) e.push("Contract duration (months)"); }
		}
		if (step === 4) ["project_name", "site_address", "city", "country"].forEach((f) => !S[f] && e.push(f.replace("_", " ")));
		if (step === 5 && S.budget_min && S.budget_max && Number(S.budget_min) > Number(S.budget_max)) e.push("Minimum budget exceeds maximum");
		return e;
	}
	function go(step) {
		if (step > S.step) for (let i = S.step; i < step; i++) { const e = validate(i); if (e.length) { MP.toast("Please complete: " + e.join(", "), "err"); S.step = i; return render(); } }
		S.step = step; save(); render(); window.scrollTo({ top: root.offsetTop - 90, behavior: "smooth" });
	}

	const views = [
		() => h("div", { class: "stack" }, h("h2", {}, "What kind of deal is this?"), h("p", { class: "muted" }, "Each model has its own pricing and fulfilment rules."),
			h("div", { class: "choice-grid" }, [["Hire", "Rent for a period — daily, weekly or monthly rates, deposit, delivery and off-hire."],
				["Sale", "Buy outright — unit prices, minimum order, delivery schedule and warranty."], ["Contract", "Long-term or project supply — monthly rates, mobilisation and periodic invoicing."]]
				.map(([t, d]) => h("button", { class: "choice" + (S.transaction_type === t ? " on" : ""), onclick: () => { S.transaction_type = t; go(1); } }, h("b", {}, t), h("span", {}, d))))),
		() => {
			const groups = cats.filter((c) => c.parent === "All Equipment");
			return h("div", { class: "stack" }, h("h2", {}, "Which equipment category?"), h("p", { class: "muted" }, "Pick the closest match — you can describe the exact items next."),
				...groups.map((g) => h("div", {}, h("h4", {}, g.category_name), h("div", { class: "choice-grid" }, cats.filter((c) => c.parent === g.name && c["allow_" + S.transaction_type.toLowerCase()]).map((c) =>
					h("button", { class: "choice" + (S.category === c.name ? " on" : ""), onclick: () => { S.category = c.name; S.items.forEach((it) => (it.category = it.category || c.name)); go(2); } },
						h("b", {}, c.category_name), h("span", {}, c.listing_count ? `${c.listing_count} listings` : "Tendered to matching suppliers")))))));
		},
		() => {
			const list = h("div", { class: "stack" });
			const draw = () => { list.innerHTML = ""; S.items.forEach((it, i) => list.append(itemRow(it, i, draw))); };
			draw();
			return h("div", { class: "stack" }, h("h2", {}, "Describe the equipment"), h("p", { class: "muted" }, "Add one line per item. Specifications help suppliers price accurately."),
				list, h("datalist", { id: "uoms" }, B.uoms.map((u) => h("option", { value: u }))),
				h("button", { class: "btn ghost", onclick: () => { S.items.push({ equipment_name: "", qty: "", uom: "Nos", condition_required: "Any", accept_alternatives: 1, category: S.category }); save(); draw(); } }, "+ Add another line"));
		},
		() => {
			const t = S.transaction_type, g = h("div", { class: "grid g2" });
			if (t === "Hire") {
				const dur = h("div", { class: "card flat", style: { gridColumn: "1/-1", background: "var(--steel-50)" } });
				const upd = () => (dur.innerHTML = days() > 0 ? `<b>${days()} days</b> <span class="muted">≈ ${(days() / 30).toFixed(1)} months · suppliers quote on this period</span>` : '<span class="muted">Choose dates to see the duration</span>');
				g.append(field("Rental start date", "required_from", { type: "date", reqd: 1, min: TODAY, onchange: upd }), field("Expected return date", "required_to", { type: "date", reqd: 1, min: TODAY, onchange: upd }), dur,
					field("Extension may be needed", "extension_possible", { type: "check" }), field("Delivery to site required", "delivery_required", { type: "check" }));
				upd();
			} else if (t === "Sale") {
				g.append(field("Expected delivery date", "expected_delivery_date", { type: "date", reqd: 1, min: TODAY }),
					field("Delivery terms", "delivery_terms", { type: "select", options: ["", "Delivered to site", "Ex-works / pickup", "Delivered and installed"] }));
			} else {
				g.append(field("Project / contract start", "contract_start", { type: "date", reqd: 1, min: TODAY }), field("Contract duration (months)", "contract_months", { type: "number", reqd: 1, min: 1 }),
					field("Expected monthly quantity", "expected_monthly_qty", { type: "number" }), h("div"),
					field("Project requirements & long-term terms", "project_requirements", { type: "textarea", full: 1, placeholder: "Phasing, mobilisation/demobilisation, framework agreement, service conditions…" }));
			}
			return h("div", { class: "stack" }, h("h2", {}, t === "Hire" ? "Hire period" : t === "Sale" ? "Delivery" : "Contract terms"), g);
		},
		() => {
			const g = h("div", { class: "grid g2" });
			if (B.sites && B.sites.length) {
				g.append(h("label", { class: "field", style: { gridColumn: "1/-1" } }, h("span", {}, "Use a saved project site"), h("select", { onchange: (e) => {
					const s = B.sites.find((x) => x.name === e.target.value); S.project_site = s ? s.name : "";
					if (s) ["project_name", "site_address", "city", "state", "country", "site_contact", "site_phone", "site_access"].forEach((k) => (S[k] = s[k] || S[k]));
					save(); render(); } }, h("option", { value: "" }, "— New site —"), B.sites.map((s) => h("option", { value: s.name, selected: S.project_site === s.name || null }, `${s.project_name} · ${s.city}`)))));
			}
			g.append(field("Project name", "project_name", { reqd: 1 }), field("Delivery location / gate", "delivery_location", { placeholder: "Gate 3, north side" }),
				field("Site address", "site_address", { type: "textarea", reqd: 1, full: 1 }), field("City", "city", { reqd: 1 }), field("State / governorate", "state"),
				field("Country", "country", { reqd: 1, list: "countries" }), h("datalist", { id: "countries" }, B.countries.map((c) => h("option", { value: c }))),
				field("Site contact", "site_contact"), field("Site phone", "site_phone", { type: "tel" }),
				field("Site accessibility", "site_access", { type: "textarea", placeholder: "Trailer access, crane, working hours, permits" }),
				field("Special requirements", "special_requirements", { type: "textarea" }));
			return h("div", { class: "stack" }, h("h2", {}, "Project & site"), h("p", { class: "muted small" }, "🔒 Suppliers see only the city until you award the tender."), g);
		},
		() => h("div", { class: "stack" }, h("h2", {}, "Commercial preferences"), h("p", { class: "muted" }, "All optional. Your budget is never shown to suppliers unless the marketplace enables it for the tender."),
			h("div", { class: "grid g2" }, field(`Budget from (${B.currency})`, "budget_min", { type: "number", min: 0 }), field(`Budget up to (${B.currency})`, "budget_max", { type: "number", min: 0 }),
				field("Preferred payment terms", "payment_terms_pref", { placeholder: "e.g. 20% advance, balance monthly" }), h("div"),
				field("Transportation required", "transport_required", { type: "check" }), field("Installation / erection required", "installation_required", { type: "check" }),
				field("Technical support on site", "technical_support", { type: "check" }), h("div"),
				field("Other commercial conditions", "other_conditions", { type: "textarea", full: 1 }))),
		() => {
			const list = h("div", { class: "stack" });
			const draw = () => { list.innerHTML = ""; S.attachments.forEach((a, i) => list.append(h("div", { class: "card flat row between", style: { padding: "10px 14px" } },
				h("div", {}, h("b", {}, a.title || a.file_name), h("div", { class: "small muted" }, a.document_type)),
				h("div", { class: "row" }, h("label", { class: "check small" }, h("input", { type: "checkbox", checked: a.share_with_suppliers ? true : null, onchange: (e) => { a.share_with_suppliers = e.target.checked ? 1 : 0; save(); } }), "Share with invited suppliers"),
					h("button", { class: "btn ghost sm", onclick: () => { S.attachments.splice(i, 1); save(); draw(); } }, "Remove"))))); };
			draw();
			if (B.user === "Guest") return h("div", { class: "stack" }, h("h2", {}, "Attachments"), h("div", { class: "empty" }, "Sign in at the last step to attach BOQs, drawings and site plans — files are stored privately."));
			const type = h("select", {}, ["BOQ", "Equipment Schedule", "Technical Specification", "Drawing", "Site Plan", "Project Document", "Other"].map((t) => h("option", {}, t)));
			const inp = h("input", { type: "file", multiple: true, style: { display: "none" }, onchange: (e) => upload(e.target.files) });
			const drop = h("div", { class: "drop", onclick: () => inp.click() }, h("b", {}, "Drop files here or click to upload"), h("div", { class: "small muted" }, "PDF, Office, DWG/DXF, images, ZIP · up to 15 MB · stored privately"));
			drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
			drop.addEventListener("dragleave", () => drop.classList.remove("over"));
			drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); upload(e.dataTransfer.files); });
			async function upload(files) { for (const f of files) { try { const r = await MP.upload(f, 0); S.attachments.push({ file: r.file_url, file_name: r.file_name, title: f.name, document_type: type.value, share_with_suppliers: 1 }); save(); draw(); } catch (e) { MP.toast(e.message, "err"); } } }
			return h("div", { class: "stack" }, h("h2", {}, "Attachments"), h("label", { class: "field" }, h("span", {}, "Document type"), type), drop, inp, list);
		},
		() => {
			const t = S.transaction_type, rows = (pairs) => h("dl", { class: "dl" }, pairs.filter((p) => p[1]).map(([k, v]) => [h("dt", {}, k), h("dd", {}, v)]));
			const period = t === "Hire" ? `${MP.date(S.required_from)} → ${MP.date(S.required_to)} (${days()} days)` : t === "Sale" ? `Delivery by ${MP.date(S.expected_delivery_date)}` : `From ${MP.date(S.contract_start)} for ${S.contract_months} months`;
			const submit = h("button", { class: "btn amber lg", onclick: () => submitAll(submit) }, B.user === "Guest" ? "Sign in & submit" : "Submit requirement");
			return h("div", { class: "stack" }, h("h2", {}, "Review & submit"),
				h("div", { class: "card flat" }, h("div", { class: "row between" }, h("h3", {}, "Requirement"), h("button", { class: "btn ghost sm", onclick: () => go(0) }, "Edit")),
					rows([["Type", t], ["Category", S.category], ["Period", period], ["Title", S.title || autoTitle()]])),
				h("div", { class: "card flat" }, h("div", { class: "row between" }, h("h3", {}, "Equipment"), h("button", { class: "btn ghost sm", onclick: () => go(2) }, "Edit")),
					MP.table([{ label: "Item", key: "equipment_name" }, { label: "Qty", html: (r) => esc(r.qty + " " + r.uom), right: 1 }, { label: "Specifications", key: "specifications" }, { label: "Alternatives", html: (r) => (r.accept_alternatives ? "Accepted" : "No") }], S.items)),
				h("div", { class: "card flat" }, h("div", { class: "row between" }, h("h3", {}, "Site"), h("button", { class: "btn ghost sm", onclick: () => go(4) }, "Edit")),
					rows([["Project", S.project_name], ["Address", S.site_address], ["City", [S.city, S.state, S.country].filter(Boolean).join(", ")], ["Site contact", [S.site_contact, S.site_phone].filter(Boolean).join(" · ")]])),
				h("div", { class: "card flat" }, h("div", { class: "row between" }, h("h3", {}, "Commercial"), h("button", { class: "btn ghost sm", onclick: () => go(5) }, "Edit")),
					rows([["Budget", S.budget_min || S.budget_max ? `${MP.money(S.budget_min || 0)} – ${MP.money(S.budget_max || 0)}` : "Not specified"], ["Payment terms", S.payment_terms_pref], ["Attachments", S.attachments.length ? S.attachments.length + " file(s)" : "None"]])),
				h("label", { class: "field" }, h("span", {}, "Requirement title (shown to suppliers)"), h("input", { value: S.title || autoTitle(), oninput: (e) => { S.title = e.target.value; save(); } })),
				h("div", { class: "row" }, submit, h("span", { class: "small muted" }, "Your request is reviewed by the platform and tendered to matched suppliers.")));
		},
	];
	const autoTitle = () => `${S.transaction_type}: ${S.items.map((i) => (i.qty ? i.qty + " × " : "") + i.equipment_name).filter(Boolean).slice(0, 2).join(", ")} — ${S.city || ""}`.slice(0, 140);

	function itemRow(it, i, redraw) {
		const set = (k) => (e) => { it[k] = e.target.type === "checkbox" ? (e.target.checked ? 1 : 0) : e.target.value; save(); };
		const sub = cats.filter((c) => !c.is_group && c["allow_" + S.transaction_type.toLowerCase()]);
		return h("div", { class: "item-row" },
			h("label", { class: "field" }, h("span", {}, `Line ${i + 1} · equipment`, h("em", {}, " *")), h("input", { value: it.equipment_name || "", placeholder: "e.g. Cuplock standard 3.0 m", oninput: set("equipment_name") })),
			h("label", { class: "field" }, h("span", {}, "Quantity", h("em", {}, " *")), h("input", { type: "number", min: 0, step: "any", value: it.qty ?? "", oninput: set("qty") })),
			h("label", { class: "field" }, h("span", {}, "Unit"), h("input", { value: it.uom || "Nos", list: "uoms", oninput: set("uom") })),
			h("label", { class: "field" }, h("span", {}, "Technical specifications"), h("input", { value: it.specifications || "", placeholder: "Size, capacity, finish, standard", oninput: set("specifications") })),
			h("div", { class: "row" }, S.items.length > 1 ? h("button", { class: "btn ghost sm", onclick: () => { S.items.splice(i, 1); save(); redraw(); } }, "✕") : ""),
			h("label", { class: "field" }, h("span", {}, "Sub-category"), h("select", { onchange: set("category") }, sub.map((c) => h("option", { value: c.name, selected: (it.category || S.category) === c.name || null }, c.category_name)))),
			h("label", { class: "field" }, h("span", {}, "Condition"), h("select", { onchange: set("condition_required") }, ["Any", "New", "Used - Good or better"].map((o) => h("option", { selected: it.condition_required === o || null }, o)))),
			h("label", { class: "field" }, h("span", {}, "Brand preference"), h("input", { value: it.brand_preference || "", oninput: set("brand_preference") })),
			h("label", { class: "field" }, h("span", {}, "Required certifications"), h("input", { value: it.certifications_required || "", placeholder: "EN 12811, third-party load test", oninput: set("certifications_required") })),
			h("label", { class: "check", style: { alignSelf: "center" } }, h("input", { type: "checkbox", checked: it.accept_alternatives ? true : null, onchange: set("accept_alternatives") }), "Alternatives OK"));
	}

	async function submitAll(btn) {
		for (let i = 0; i < 7; i++) { const e = validate(i); if (e.length) { MP.toast("Please complete: " + e.join(", "), "err"); return go(i); } }
		if (B.user === "Guest") { save(); location.href = "/login?redirect-to=" + encodeURIComponent("/marketplace/post-requirement?resume=1"); return; }
		btn.disabled = true;
		try {
			if (!B.customer) { await MP.call("public.register_customer", { data: { customer_type: "Company", company_name: "", full_name: "", email: B.user } }); }
			const data = { ...S, title: S.title || autoTitle() };
			["step"].forEach((k) => delete data[k]);
			const r = await MP.call("customer.request_save", { data, submit: 1 });
			store.clear();
			root.innerHTML = "";
			root.style.gridTemplateColumns = "1fr";
			root.append(h("div", { class: "card center fade-in", style: { padding: "48px" } }, h("span", { class: "eyebrow" }, "Requirement submitted"), h("h1", {}, r.name),
				h("p", { class: "muted" }, r.tender ? `Tender ${r.tender} is ${r.status === "Tendered" ? "live — matched suppliers have been invited" : "awaiting marketplace review"}. We will notify you as offers arrive.` : "Saved."),
				h("div", { class: "row", style: { justifyContent: "center" } }, h("a", { class: "btn", href: "/marketplace/account/requests/" + encodeURIComponent(r.name) }, "Track this request"), h("a", { class: "btn ghost", href: "/marketplace/post-requirement" }, "Post another"))));
		} catch (e) { MP.toast(e.message, "err"); btn.disabled = false; }
	}

	function render() {
		root.innerHTML = "";
		root.append(h("ol", { class: "wiz-steps" }, STEPS.map((s, i) => h("li", { class: i === S.step ? "on" : i < S.step ? "done" : "", style: { cursor: i < S.step ? "pointer" : "default" }, onclick: () => i < S.step && go(i) }, h("b", {}, i < S.step ? "✓" : i + 1), s))));
		const body = h("div", { class: "card", style: { padding: "28px" } }, views[S.step]());
		if (S.step > 0 && S.step < 7) body.append(h("div", { class: "row between", style: { marginTop: "24px", borderTop: "1px solid var(--steel-200)", paddingTop: "18px" } },
			h("button", { class: "btn ghost", onclick: () => go(S.step - 1) }, "← Back"), S.step >= 2 || S.step === 0 ? h("button", { class: "btn", onclick: () => go(S.step + 1) }, "Continue →") : h("span")));
		else if (S.step === 7) body.prepend(h("button", { class: "btn ghost sm", style: { marginBottom: "12px" }, onclick: () => go(6) }, "← Back"));
		root.append(body);
	}
	render();
})();
