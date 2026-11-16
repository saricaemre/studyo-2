// Yazı tanıma (macOS Vision, yerel): ölçüm ekranda ne yazdığını okur (canlı veri: "ekrandaki rakamlar dondurulmuş veriyle aynı mı").
// Derleme pipeline/veri.py → ocr_hazir(): swiftc -O ocr.swift -o out/_araclar/ocr (Xcode komut satırı araçları; yoksa ölçüm göz satırına düşer).
// Kullanım: ocr <png> … → her dosya için bir JSON satırı: {"dosya", "satirlar": [{"metin", "guven", "kutu": [x, y, w, h]}]} (kutu 0–1, sol üstten)
import AppKit
import Foundation
import Vision

for yol in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: yol), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        print("{\"dosya\": \"\(yol)\", \"hata\": \"okunamadı\"}")
        continue
    }
    let istek = VNRecognizeTextRequest()
    istek.recognitionLevel = .accurate
    istek.usesLanguageCorrection = false
    istek.recognitionLanguages = ["tr-TR", "en-US"]
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([istek])
    var satirlar: [[String: Any]] = []
    for g in istek.results ?? [] {
        if let a = g.topCandidates(1).first {
            let b = g.boundingBox
            satirlar.append(["metin": a.string, "guven": a.confidence, "kutu": [b.minX, 1 - b.maxY, b.width, b.height]])
        }
    }
    let d = try! JSONSerialization.data(withJSONObject: ["dosya": yol, "satirlar": satirlar])
    print(String(data: d, encoding: .utf8)!)
}
