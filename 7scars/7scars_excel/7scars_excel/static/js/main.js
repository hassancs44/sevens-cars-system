async function fetchRows(q, limit) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (limit) params.set("limit", limit);
  const res = await fetch(`/api/records?${params.toString()}`);
  return res.json();
}

function renderTable(rows, mountEl) {
  if (!rows || rows.length === 0) {
    mountEl.innerHTML = `<div class="empty">🚫 لا توجد بيانات</div>`;
    return;
  }
  const thead = `
    <thead>
      <tr>
        <th>لوحة</th>
        <th>اللون</th>
        <th>تاريخ تغيير الزيت</th>
        <th>عداد</th>
        <th>ممشى الزيت</th>
        <th>الشركة</th>
        <th>الموديل</th>
      </tr>
    </thead>`;
  const tbody = `
    <tbody>
      ${rows.map(r => `
        <tr>
          <td>${r.plate || ""}</td>
          <td>${r.color || ""}</td>
          <td>${r.oil_date || ""}</td>
          <td>${r.odometer || ""}</td>
          <td>${r.oil_mileage || ""}</td>
          <td>${r.make || ""}</td>
          <td>${r.model || ""}</td>
        </tr>`).join("")}
    </tbody>`;
  mountEl.innerHTML = `<table class="table">${thead}${tbody}</table>`;
}

function initPage(cfg) {
  const {
    scope, tableWrapId, searchId, filterId, refreshId, formId, statusId
  } = cfg;

  const wrap = document.getElementById(tableWrapId);
  const search = document.getElementById(searchId);
  const filter = document.getElementById(filterId);
  const refreshBtn = document.getElementById(refreshId);

  async function load() {
    const q = (search?.value || "").trim();
    const limit = (filter?.value || "all").trim();
    const { success, rows } = await fetchRows(q, limit);
    if (success) renderTable(rows, wrap);
  }

  // تفاعلات البحث والفلترة
  search?.addEventListener("input", load);
  filter?.addEventListener("change", load);
  refreshBtn?.addEventListener("click", load);
  load();

  // صفحة الصيانة: إرسال النموذج
  if (scope === "maintenance" && formId) {
    const form = document.getElementById(formId);
    const statusEl = statusId ? document.getElementById(statusId) : null;

    form?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const body = {
        plate: document.getElementById("plate").value,
        color: document.getElementById("color").value,
        oil_date: document.getElementById("oil_date").value,
        odometer: document.getElementById("odometer").value,
        oil_mileage: document.getElementById("oil_mileage").value,
        make: document.getElementById("make").value,
        model: document.getElementById("model").value
      };
      const res = await fetch("/api/records", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify(body)
      });
      const data = await res.json();
      if (statusEl) {
        statusEl.textContent = data.message || (data.success ? "تم الحفظ ✅" : "حدث خطأ");
        statusEl.style.color = data.success ? "#0a7c2f" : "#b80d2e";
      }
      load();
      form.reset();
    });
  }
}
