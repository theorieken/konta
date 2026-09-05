// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "KontaKit",
    defaultLocalization: "de",
    platforms: [.iOS("26.0"), .macOS("26.0")],
    products: [.library(name: "KontaKit", targets: ["KontaKit"])],
    targets: [
        .target(name: "KontaKit"),
        .testTarget(name: "KontaKitTests", dependencies: ["KontaKit"], resources: [.copy("Fixtures")])
    ]
)
