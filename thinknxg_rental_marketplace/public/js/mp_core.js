/* thinkNXG Rental Marketplace — shared client core (no build step).
   API calls carry the CSRF token; the server resolves who is acting and recomputes every amount. */
(function () {
	const MP = (window.MP = window.MP || {});
	const NS = "thinknxg_rental_marketplace.api.";
	MP.csrf = document.querySelector('meta[name="csrf-token"]')?.content || window.csrf_token || "";
	MP.currency = document.body.dataset.currency || "OMR";

	// ------------------------------------------------------------------ API
	MP.call = async function (method, args = {}, opts = {}) {
		const post = opts.post ?? true; // every call is a CSRF-protected POST
		const url = "/api/method/" + (method.startsWith("thinknxg_") ? method : NS + method);
		const body = new URLSearchParams();
		Object.entries(args).forEach(([k, v]) => v !== undefined && v !== null && body.append(k, typeof v === "object" ? JSON.stringify(v) : v));
		const res = await fetch(post ? url : url + "?" + body.toString(), {
			method: post ? "POST" : "GET", credentials: "same-origin",
			headers: { Accept: "application/json", "X-Frappe-CSRF-Token": MP.csrf, ...(post ? { "Content-Type": "application/x-www-form-urlencoded" } : {}) },
			body: post ? body : undefined,
		});
		let data = {};
		try { data = await res.json(); } catch (e) { /* non-JSON */ }
		if (!res.ok || data.exc_type) {
			let msg = "Something went wrong.";
			try { msg = JSON.parse(JSON.parse(data._server_messages)[0]).message; } catch (e) { msg = data.exception || data.message || msg; }
			msg = String(msg).replace(/<[^>]+>/g, "");
			const m = msg.match(/^\[([A-Z_]+)\]\s*(.*)$/);
			const err = new Error(m ? m[2] : msg.replace(/^[\w.]+Error: /, ""));
			err.code = m ? m[1] : res.status === 403 ? "FORBIDDEN" : "ERROR";
			err.status = res.status;
			if (res.status === 403 && /LOGIN_REQUIRED|Guest|not permitted/i.test(msg)) err.code = "LOGIN_REQUIRED";
			throw err;
		}
		return data.message;
	};
	MP.safe = async function (fn, okMsg) {
		try { const r = await fn(); if (okMsg) MP.toast(okMsg, "ok"); return r; }
		catch (e) { MP.toast(e.message, "err"); if (e.code === "LOGIN_REQUIRED") location.href = "/login?redirect-to=" + encodeURIComponent(location.pathname); throw e; }
	};
	MP.upload = async function (file, isPublic = 0) {
		const fd = new FormData(); fd.append("file", file); fd.append("public", isPublic ? 1 : 0);
		const res = await fetch("/api/method/" + NS + "files.upload", { method: "POST", body: fd, credentials: "same-origin", headers: { "X-Frappe-CSRF-Token": MP.csrf, Accept: "application/json" } });
		const data = await res.json().catch(() => ({}));
		if (!res.ok) { let m = "Upload failed"; try { m = JSON.parse(JSON.parse(data._server_messages)[0]).message.replace(/^\[[A-Z_]+\]\s*/, ""); } catch (e) {} throw new Error(m); }
		return data.message;
	};
	MP.fileLink = (url) => (url && url.startsWith("/private/") ? "/api/method/" + NS + "files.download?file_url=" + encodeURIComponent(url) : url);

	// ------------------------------------------------------------------ DOM helpers
	const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
	MP.esc = (s) => (s === null || s === undefined ? "" : String(s).replace(/[&<>"']/g, (c) => ESC[c]));
	MP.h = function (tag, attrs, ...kids) {
		const el = document.createElement(tag);
		for (const [k, v] of Object.entries(attrs || {})) {
			if (v === false || v === null || v === undefined) continue;
			if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
			else if (k === "html") el.innerHTML = v;
			else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
			else el.setAttribute(k, v === true ? "" : v);
		}
		kids.flat(Infinity).forEach((c) => c !== null && c !== undefined && c !== false && el.append(c instanceof Node ? c : document.createTextNode(String(c))));
		return el;
	};
	MP.frag = (html) => { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content; };
	MP.$ = (s, r = document) => r.querySelector(s);
	MP.$$ = (s, r = document) => Array.from(r.querySelectorAll(s));

	// ------------------------------------------------------------------ formatting
	const THREE = ["OMR", "KWD", "BHD", "JOD", "TND", "LYD", "IQD"];
	MP.money = (v, cur) => {
		cur = cur || MP.currency; const d = THREE.includes(cur) ? 3 : 2;
		if (v === null || v === undefined || v === "") return "—";
		return cur + " " + Number(v).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });
	};
	MP.num = (v) => (v === null || v === undefined ? "—" : Number(v).toLocaleString());
	MP.date = (v) => (v ? new Date(String(v).replace(" ", "T")).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" }) : "—");
	MP.dt = (v) => (v ? new Date(String(v).replace(" ", "T")).toLocaleString(undefined, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—");
	MP.ago = (v) => { if (!v) return ""; const s = (Date.now() - new Date(String(v).replace(" ", "T"))) / 1000;
		return s < 60 ? "just now" : s < 3600 ? Math.round(s / 60) + "m ago" : s < 86400 ? Math.round(s / 3600) + "h ago" : Math.round(s / 86400) + "d ago"; };
	MP.until = (v) => { const s = (new Date(String(v).replace(" ", "T")) - Date.now()) / 1000; if (s <= 0) return "closed";
		const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60); return d ? `${d}d ${h}h left` : h ? `${h}h ${m}m left` : `${m}m left`; };
	MP.stars = (r) => { const n = Math.round(Number(r) || 0); return "★★★★★".slice(0, n) + "☆☆☆☆☆".slice(0, 5 - n); };
	const TONE = { green: ["Approved", "Published", "Succeeded", "Paid", "Completed", "Accepted", "Awarded", "Active", "Confirmed", "Answered", "Resolved", "Earned", "Settled", "Commercially Accepted", "Technically Accepted", "Offer Submitted", "Booked"],
		blue: ["Bidding Open", "Submitted", "Under Review", "Evaluation", "Invitation Sent", "Tendered", "Offers Received", "On Hire", "Dispatched", "Delivered", "Mobilized", "Trial", "Interested", "Viewed", "Pending", "Requested", "Initiated", "Accrued", "Approved_", "Payout Initiated"],
		amber: ["Draft", "Documents Pending", "Pending Payment", "Bidding Closed", "Grace", "Off-Hire Requested", "Returned", "Demobilized", "Open", "Invited", "Pending Moderation", "Partially Refunded", "Return Due", "New"],
		red: ["Rejected", "Suspended", "Cancelled", "Expired", "Withdrawn", "Technically Rejected", "Not Awarded", "Failed", "Deactivated", "Reversed", "Declined", "Excluded", "Hidden", "Restricted", "Escalated"] };
	MP.badge = (s) => { const tone = Object.keys(TONE).find((k) => TONE[k].includes(s)) || ""; return `<span class="badge ${tone}">${MP.esc(s || "—")}</span>`; };

	// ------------------------------------------------------------------ feedback
	MP.toast = function (msg, kind = "") {
		let box = MP.$(".toasts"); if (!box) { box = MP.h("div", { class: "toasts" }); document.body.append(box); }
		const t = MP.h("div", { class: "toast " + kind }, msg); box.append(t); setTimeout(() => t.remove(), kind === "err" ? 6500 : 3500);
	};
	MP.modal = function ({ title, body, actions = [], wide = false }) {
		return new Promise((resolve) => {
			const back = MP.h("div", { class: "modal-back" });
			const close = (v) => { back.remove(); resolve(v); };
			const content = typeof body === "string" ? MP.frag(body) : body;
			const m = MP.h("div", { class: "modal", style: wide ? { width: "min(920px,100%)" } : null },
				MP.h("header", {}, MP.h("h3", {}, title), MP.h("button", { class: "btn ghost sm", onclick: () => close(null) }, "✕")),
				MP.h("div", { class: "mbody" }, content),
				actions.length ? MP.h("footer", {}, actions.map((a) => MP.h("button", { class: "btn " + (a.class || ""), onclick: async (e) => {
					if (!a.handler) return close(a.value ?? null);
					e.target.disabled = true;
					try { const v = await a.handler(m); if (v !== false) close(v ?? true); } catch (err) { MP.toast(err.message, "err"); } finally { e.target.disabled = false; }
				} }, a.label))) : null);
			back.append(m); back.addEventListener("click", (e) => e.target === back && close(null)); document.body.append(back);
			setTimeout(() => m.querySelector("input,select,textarea")?.focus(), 30);
		});
	};
	MP.confirm = (title, text, label = "Confirm", cls = "") => MP.modal({ title, body: `<p>${MP.esc(text)}</p>`, actions: [{ label: "Back", class: "ghost", value: false }, { label, class: cls, value: true }] });
	MP.prompt = (title, fields, label = "Save") => MP.modal({ title, body: MP.formFields(fields), actions: [{ label: "Cancel", class: "ghost", value: null },
		{ label, handler: (m) => { const v = MP.readForm(m); const miss = fields.filter((f) => f.reqd && !v[f.name]); if (miss.length) { MP.toast("Required: " + miss.map((f) => f.label).join(", "), "err"); return false; } return v; } }] });

	// fields: [{name,label,type,options,reqd,value,placeholder,help}]
	MP.formFields = function (fields, cls = "grid g2") {
		const wrap = MP.h("div", { class: cls });
		fields.forEach((f) => {
			let input;
			const common = { name: f.name, placeholder: f.placeholder || "", required: f.reqd || null };
			if (f.type === "select") input = MP.h("select", common, (f.options || []).map((o) => { const [v, l] = Array.isArray(o) ? o : [o, o]; return MP.h("option", { value: v, selected: String(f.value ?? "") === String(v) || null }, l); }));
			else if (f.type === "textarea") input = MP.h("textarea", common, f.value ?? "");
			else if (f.type === "check") return wrap.append(MP.h("label", { class: "check", style: { gridColumn: f.full ? "1/-1" : null } }, MP.h("input", { type: "checkbox", name: f.name, checked: f.value ? true : null }), f.label));
			else input = MP.h("input", { ...common, type: f.type || "text", value: f.value ?? "", step: f.step || (f.type === "number" ? "any" : null), min: f.min ?? null });
			wrap.append(MP.h("label", { class: "field", style: { gridColumn: f.full ? "1/-1" : null } }, MP.h("span", {}, f.label, f.reqd ? MP.h("em", {}, " *") : ""), input, f.help ? MP.h("small", { class: "muted" }, f.help) : null));
		});
		return wrap;
	};
	MP.readForm = function (root) {
		const out = {};
		MP.$$("input[name],select[name],textarea[name]", root).forEach((el) => {
			if (el.type === "checkbox") out[el.name] = el.checked ? 1 : 0;
			else if (el.type === "number") out[el.name] = el.value === "" ? null : Number(el.value);
			else out[el.name] = el.value.trim();
		});
		return out;
	};
	MP.uuid = () => (crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2));

	// ------------------------------------------------------------------ icons (original line set)
	const P = {
		home: "M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z", doc: "M7 3h7l5 5v13H7zM14 3v5h5", gavel: "M14 4l6 6-3 3-6-6zM11 7l-7 7 3 3 7-7M3 21h10",
		tag: "M3 12V4h8l10 10-8 8zM7.5 7.5h.01", box: "M3 7l9-4 9 4v10l-9 4-9-4zM3 7l9 4 9-4M12 11v10", truck: "M3 6h11v10H3zM14 10h4l3 3v3h-7M6.5 19a1.5 1.5 0 1 0 0-.01M17.5 19a1.5 1.5 0 1 0 0-.01",
		card: "M3 6h18v12H3zM3 10h18", star: "M12 3l2.7 5.6 6.3.9-4.5 4.4 1 6.1L12 17l-5.5 3 1-6.1L3 9.5l6.3-.9z", user: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0",
		users: "M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM2 20a7 7 0 0 1 14 0M16 4a3.5 3.5 0 0 1 0 7M18 20a6 6 0 0 0-3-5.2", pin: "M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11zM12 12.5a2.5 2.5 0 1 0 0-5",
		bell: "M6 16V11a6 6 0 0 1 12 0v5l2 2H4zM10 21h4", chart: "M4 20V10M10 20V4M16 20v-7M22 20H2", shield: "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z", cog: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1-2 2-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21h-3v-.1a1.6 1.6 0 0 0-2.7-1.1l-.1.1-2-2 .1-.1A1.6 1.6 0 0 0 4.6 15H3v-3h.1a1.6 1.6 0 0 0 1.1-2.7l-.1-.1 2-2 .1.1A1.6 1.6 0 0 0 9 6.1V3h3v.1a1.6 1.6 0 0 0 2.7 1.1l.1-.1 2 2-.1.1a1.6 1.6 0 0 0 1.1 2.7H21v3h-.1a1.6 1.6 0 0 0-1.5 1z",
		money: "M3 7h18v10H3zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM6 10v4M18 10v4", alert: "M12 3l10 18H2zM12 10v4M12 17h.01", scale: "M12 3v18M5 21h14M5 7h14M5 7l-3 7a3 3 0 0 0 6 0zM19 7l-3 7a3 3 0 0 0 6 0z",
		plus: "M12 5v14M5 12h14", list: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01", grid: "M3 3h8v8H3zM13 3h8v8h-8zM3 13h8v8H3zM13 13h8v8h-8z", layers: "M12 3l9 5-9 5-9-5zM3 13l9 5 9-5",
		scaffold: "M5 3v18M19 3v18M5 7h14M5 12h14M5 17h14M5 7l14 5M19 12L5 17", formwork: "M3 5h18v4H3zM5 9v10M19 9v10M9 9v10M15 9v10M3 19h18", excavator: "M3 18h11M4 18v-3h9v3M7 15V11h4l2 4M13 11l4-6 4 3-3 2M18 10l1 4h-3", clamp: "M7 4h10v5H7zM9 9v11M15 9v11M5 20h14",
	};
	MP.icon = (k, size = 18, color = "currentColor") => `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="${color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="${P[k] || P.box}"/></svg>`;

	// ------------------------------------------------------------------ tiny SPA router for the portals
	MP.portal = function ({ base, routes, onNav }) {
		const view = MP.$("#view");
		const title = MP.$("#page-title");
		async function go(path, push = true) {
			if (push) history.pushState({}, "", path);
			const rel = path.replace(base, "").replace(/^\/+|\/+$/g, "").split("?")[0];
			let handler = routes[""], params = {};
			for (const [pattern, fn] of Object.entries(routes)) {
				const keys = []; const re = new RegExp("^" + pattern.replace(/:(\w+)/g, (_, k) => (keys.push(k), "([^/]+)")) + "$");
				const m = rel.match(re); if (m) { handler = fn; keys.forEach((k, i) => (params[k] = decodeURIComponent(m[i + 1]))); break; }
			}
			MP.$$(".side nav a").forEach((a) => a.classList.toggle("on", !!(a.dataset.match && new RegExp(a.dataset.match).test(rel))));
			document.querySelector(".shell")?.classList.remove("nav-open");
			view.innerHTML = '<div class="spinner"></div>';
			try {
				const out = await handler(params, new URLSearchParams(location.search));
				if (out && out.title && title) { title.textContent = out.title; document.title = out.title + " · thinkNXG Marketplace"; }
				view.innerHTML = ""; if (out && out.el) view.append(out.el); view.firstElementChild?.classList.add("fade-in");
			} catch (e) {
				if (e.code === "LOGIN_REQUIRED") return (location.href = "/login?redirect-to=" + encodeURIComponent(location.pathname));
				view.innerHTML = `<div class="empty"><h3>${MP.esc(e.code === "FORBIDDEN" || e.status === 403 ? "No access" : "Could not load this page")}</h3><p>${MP.esc(e.message)}</p></div>`;
			}
			onNav && onNav(rel);
			window.scrollTo(0, 0);
		}
		document.addEventListener("click", (e) => {
			const a = e.target.closest("a[href]"); if (!a || a.target || e.metaKey || e.ctrlKey) return;
			const href = a.getAttribute("href"); if (href.startsWith(base) && !a.hasAttribute("data-full")) { e.preventDefault(); go(href); }
		});
		window.addEventListener("popstate", () => go(location.pathname + location.search, false));
		MP.go = go; MP.reload = () => go(location.pathname + location.search, false);
		MP.$(".menu-btn")?.addEventListener("click", () => MP.$(".shell").classList.toggle("nav-open"));
		go(location.pathname + location.search, false);
	};

	MP.table = function (cols, rows, { onclick, empty = "Nothing here yet." } = {}) {
		if (!rows || !rows.length) return MP.h("div", { class: "empty" }, empty);
		const t = MP.h("table", { class: "t" }, MP.h("thead", {}, MP.h("tr", {}, cols.map((c) => MP.h("th", { class: c.right ? "right" : "" }, c.label)))),
			MP.h("tbody", {}, rows.map((r) => { const tr = MP.h("tr", { class: onclick ? "click" : "" }, cols.map((c) => MP.h("td", { class: c.right ? "right nowrap" : "", html: c.html ? c.html(r) : MP.esc(r[c.key] ?? "—") })));
				if (onclick) tr.addEventListener("click", (e) => { if (!e.target.closest("button,a")) onclick(r); }); return tr; })));
		return MP.h("div", { class: "table-wrap" }, t);
	};
	MP.kpis = (items) => MP.h("div", { class: "grid g4" }, items.map((k, i) => MP.h(k.href ? "a" : "div", { class: "card kpi " + (i === 0 ? "accent" : ""), href: k.href || null }, MP.h("span", {}, k.label), MP.h("b", {}, k.value))));
	MP.notifPanel = async function (ns) {
		const data = await MP.call(ns + ".notifications");
		const body = MP.h("div", { class: "stack" }, data.rows.length ? data.rows.map((n) => MP.h("a", { href: n.link || "#", class: "card flat", style: { display: "block", padding: "12px 14px", background: n.read ? "#fff" : "var(--blue-soft)" } },
			MP.h("b", { style: { color: "var(--navy)" } }, n.title), MP.h("div", { class: "small muted" }, n.message || ""), MP.h("div", { class: "tiny muted" }, MP.ago(n.creation)))) : MP.h("div", { class: "empty" }, "No notifications"));
		MP.modal({ title: "Notifications", body, actions: [{ label: "Mark all read", class: "ghost", handler: async () => { await MP.call(ns + ".notifications_read"); MP.$(".bell i")?.remove(); } }] });
	};
	MP.setBell = (n) => { const b = MP.$(".bell"); if (!b) return; b.querySelector("i")?.remove(); if (n) b.append(MP.h("i", {}, n > 99 ? "99+" : n)); };

	// public nav burger
	document.addEventListener("click", (e) => { if (e.target.closest(".burger")) MP.$(".nav")?.classList.toggle("open"); });
})();
