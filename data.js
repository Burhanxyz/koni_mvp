// Menu Data - Fetched dynamically from backend

const CUSTOMIZATION = {
  suhu: [
    { value: "panas", label: "Panas" },
    { value: "dingin", label: "Dingin" }
  ],
  manis: [
    { value: "normal", label: "Normal" },
    { value: "less", label: "Less Sugar" },
    { value: "no", label: "No Sugar" }
  ]
};

const FLOOR_OPTIONS = [
  "Lantai 1", "Lantai 2", "Lantai 3", "Lantai 4", "Lantai 5", "Lantai 6", "Lantai 7", "Lantai 8"
];

const ORDER_TIMELINE_STEPS = [
  { key: "received", label: "Pesanan Diterima", desc: "Pesanan telah diterima oleh sistem" },
  { key: "confirmed", label: "Pembayaran Dikonfirmasi", desc: "Pembayaran berhasil diverifikasi" },
  { key: "preparing", label: "Sedang Dibuat Barista", desc: "Pesananmu sedang diracik" },
  { key: "ready", label: "Siap Diambil", desc: "Pesanan siap untuk diambil / diantar" },
  { key: "completed", label: "Pesanan Selesai", desc: "Pesanan telah selesai" }
];

function formatRupiah(num) {
  return "Rp " + num.toLocaleString("id-ID");
}

function generateOrderId() {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  let id = "KONI-";
  for (let i = 0; i < 4; i++) id += chars.charAt(Math.floor(Math.random() * chars.length));
  return id;
}
