import AppKit
import Foundation

// Reproducible source artwork for the iOS, iPadOS and macOS asset catalog.
let output = URL(fileURLWithPath: CommandLine.arguments[1])
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)

func render(size: Int, mac: Bool, name: String) throws {
    let bitmap = NSBitmapImageRep(
        bitmapDataPlanes: nil,
        pixelsWide: size,
        pixelsHigh: size,
        bitsPerSample: 8,
        samplesPerPixel: 4,
        hasAlpha: true,
        isPlanar: false,
        colorSpaceName: .deviceRGB,
        bytesPerRow: 0,
        bitsPerPixel: 0
    )!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)

    let side = CGFloat(size)
    NSColor.white.setFill()
    NSRect(x: 0, y: 0, width: side, height: side).fill()

    let inset = mac ? side * 0.075 : 0
    let rect = NSRect(x: inset, y: inset, width: side - inset * 2, height: side - inset * 2)
    let background = NSBezierPath(
        roundedRect: rect,
        xRadius: mac ? side * 0.20 : 0,
        yRadius: mac ? side * 0.20 : 0
    )
    NSGradient(
        colorsAndLocations:
            (NSColor(srgbRed: 0.16, green: 0.70, blue: 1.00, alpha: 1), 0),
            (NSColor(srgbRed: 0.02, green: 0.42, blue: 0.96, alpha: 1), 0.48),
            (NSColor(srgbRed: 0.01, green: 0.16, blue: 0.74, alpha: 1), 1)
    )!.draw(in: background, angle: -55)

    let font = NSFont.systemFont(ofSize: side * 0.58, weight: .semibold)
    let euro = NSString(string: "€")
    let attributes: [NSAttributedString.Key: Any] = [
        .font: font,
        .foregroundColor: NSColor.white,
    ]
    let bounds = euro.size(withAttributes: attributes)
    euro.draw(
        at: NSPoint(
            x: (side - bounds.width) / 2,
            y: (side - bounds.height) / 2 + side * 0.015
        ),
        withAttributes: attributes
    )

    NSGraphicsContext.restoreGraphicsState()
    try bitmap.representation(using: .png, properties: [:])!
        .write(to: output.appendingPathComponent(name))
}

var entries: [[String: String]] = []
try render(size: 1024, mac: false, name: "ios-1024.png")
entries.append([
    "idiom": "universal",
    "platform": "ios",
    "size": "1024x1024",
    "filename": "ios-1024.png",
])
for size in [16, 32, 128, 256, 512] {
    for scale in [1, 2] {
        let name = "mac-\(size)@\(scale)x.png"
        try render(size: size * scale, mac: true, name: name)
        entries.append([
            "idiom": "mac",
            "size": "\(size)x\(size)",
            "scale": "\(scale)x",
            "filename": name,
        ])
    }
}
let manifest: [String: Any] = [
    "images": entries,
    "info": ["author": "xcode", "version": 1],
]
try JSONSerialization.data(withJSONObject: manifest, options: [.prettyPrinted, .sortedKeys])
    .write(to: output.appendingPathComponent("Contents.json"))
