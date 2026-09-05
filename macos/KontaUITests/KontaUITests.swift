import XCTest

@MainActor
final class KontaUITests: XCTestCase {
    func testSidebarAndReadOnlyPreview() throws {
        let app = XCUIApplication()
        app.launchArguments = ["--demo"]
        app.launch()
        XCTAssertTrue(app.staticTexts["Vorschau mit Beispieldaten"].waitForExistence(timeout: 10))
        let overview = XCTAttachment(screenshot: app.screenshot())
        overview.name = "Konta Mac Übersicht"; overview.lifetime = .keepAlways; add(overview)
        app.outlines.staticTexts["Ausgaben"].click()
        XCTAssertTrue(app.segmentedControls.buttons["Verträge & Kredite"].waitForExistence(timeout: 5))
        app.segmentedControls.buttons["Verträge & Kredite"].click()
        XCTAssertTrue(app.staticTexts["Miete Zuhause"].waitForExistence(timeout: 5))
        app.staticTexts["Miete Zuhause"].click()
        XCTAssertTrue(app.buttons["Bearbeiten"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["Bearbeiten"].isEnabled)
        app.buttons["Schließen"].click()
        app.outlines.staticTexts["Haushalt"].click()
        XCTAssertTrue(app.buttons["Konten"].waitForExistence(timeout: 5))
        app.buttons["Konten"].click()
        XCTAssertTrue(app.staticTexts["Gemeinschaftskonto"].waitForExistence(timeout: 5))
    }
}
