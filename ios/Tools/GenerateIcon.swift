import AppKit
import Foundation

// Code-drawn artwork keeps the two app targets on one reproducible icon design.
let output = URL(fileURLWithPath: CommandLine.arguments[1])
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
func render(size: Int, mac: Bool, name: String) throws {
    let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: size, pixelsHigh: size, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)
    let s = CGFloat(size)
    let inset = mac ? s * 0.08 : 0
    let rect = NSRect(x: inset, y: inset, width: s - inset * 2, height: s - inset * 2)
    let background = NSBezierPath(roundedRect: rect, xRadius: mac ? s * 0.19 : 0, yRadius: mac ? s * 0.19 : 0)
    NSGradient(starting: NSColor(srgbRed: 0.54, green: 0.44, blue: 0.95, alpha: 1), ending: NSColor(srgbRed: 0.31, green: 0.22, blue: 0.73, alpha: 1))!.draw(in: background, angle: -65)
    NSColor.white.setStroke()
    let path = NSBezierPath()
    path.lineWidth = s * 0.075; path.lineCapStyle = .round; path.lineJoinStyle = .round
    path.move(to: NSPoint(x: s * 0.28, y: s * 0.66)); path.line(to: NSPoint(x: s * 0.28, y: s * 0.32)); path.line(to: NSPoint(x: s * 0.69, y: s * 0.32)); path.stroke()
    let chart = NSBezierPath(); chart.lineWidth = s * 0.068; chart.lineCapStyle = .round; chart.lineJoinStyle = .round
    chart.move(to: NSPoint(x: s * 0.39, y: s * 0.44)); chart.line(to: NSPoint(x: s * 0.49, y: s * 0.55)); chart.line(to: NSPoint(x: s * 0.58, y: s * 0.49)); chart.line(to: NSPoint(x: s * 0.71, y: s * 0.65)); chart.stroke()
    let star = NSBezierPath(); let cx = s * 0.69, cy = s * 0.76, r = s * 0.083
    star.move(to: NSPoint(x: cx, y: cy+r))
    star.curve(to: NSPoint(x: cx+r, y: cy), controlPoint1: NSPoint(x: cx+r*0.18, y: cy+r*0.18), controlPoint2: NSPoint(x: cx+r*0.18, y: cy+r*0.18))
    star.curve(to: NSPoint(x: cx, y: cy-r), controlPoint1: NSPoint(x: cx+r*0.18, y: cy-r*0.18), controlPoint2: NSPoint(x: cx+r*0.18, y: cy-r*0.18))
    star.curve(to: NSPoint(x: cx-r, y: cy), controlPoint1: NSPoint(x: cx-r*0.18, y: cy-r*0.18), controlPoint2: NSPoint(x: cx-r*0.18, y: cy-r*0.18))
    star.curve(to: NSPoint(x: cx, y: cy+r), controlPoint1: NSPoint(x: cx-r*0.18, y: cy+r*0.18), controlPoint2: NSPoint(x: cx-r*0.18, y: cy+r*0.18)); star.close(); NSColor.white.setFill(); star.fill()
    NSGraphicsContext.restoreGraphicsState()
    try bitmap.representation(using: .png, properties: [:])!.write(to: output.appendingPathComponent(name))
}
var entries: [[String: String]] = []
try render(size: 1024, mac: false, name: "ios-1024.png")
entries.append(["idiom": "universal", "platform": "ios", "size": "1024x1024", "filename": "ios-1024.png"])
for size in [16,32,128,256,512] {
    for scale in [1,2] {
        let name = "mac-\(size)@\(scale)x.png"
        try render(size: size * scale, mac: true, name: name)
        entries.append(["idiom": "mac", "size": "\(size)x\(size)", "scale": "\(scale)x", "filename": name])
    }
}
let manifest: [String: Any] = ["images": entries, "info": ["author": "xcode", "version": 1]]
try JSONSerialization.data(withJSONObject: manifest, options: [.prettyPrinted, .sortedKeys]).write(to: output.appendingPathComponent("Contents.json"))
