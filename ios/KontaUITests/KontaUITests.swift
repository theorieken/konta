import XCTest

@MainActor
final class KontaUITests: XCTestCase {
    func testNativeNavigationAndReadOnlyPreview() throws {
        let app = XCUIApplication()
        app.launchArguments = ["--demo"]
        app.launch()
        XCTAssertTrue(app.staticTexts["Vorschau mit Beispieldaten"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.tabBars.buttons["Übersicht"].exists)
        let overview = XCTAttachment(screenshot: app.screenshot())
        overview.name = "Konta iPhone Übersicht"; overview.lifetime = .keepAlways; add(overview)
        app.tabBars.buttons["Ausgaben"].tap()
        XCTAssertTrue(app.segmentedControls.buttons["Verträge & Kredite"].waitForExistence(timeout: 5))
        app.segmentedControls.buttons["Verträge & Kredite"].tap()
        XCTAssertTrue(app.staticTexts["Miete Zuhause"].waitForExistence(timeout: 5))
        app.staticTexts["Miete Zuhause"].tap()
        XCTAssertTrue(app.buttons["Bearbeiten"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["Bearbeiten"].isEnabled)
        app.buttons["Schließen"].tap()
        app.tabBars.buttons["Einnahmen"].tap()
        app.segmentedControls.buttons["Regelmäßig"].tap()
        XCTAssertTrue(app.staticTexts["Gehalt Alex"].waitForExistence(timeout: 5))
        app.tabBars.buttons["Haushalt"].tap()
        XCTAssertTrue(app.buttons["Konten"].waitForExistence(timeout: 5))
        app.buttons["Konten"].tap()
        XCTAssertTrue(app.staticTexts["Gemeinschaftskonto"].waitForExistence(timeout: 5))
    }
}
