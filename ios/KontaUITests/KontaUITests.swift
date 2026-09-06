import XCTest

@MainActor
final class KontaUITests: XCTestCase {
    private func keepScreenshot(_ name: String, app: XCUIApplication) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    private func tab(_ name: String, app: XCUIApplication) -> XCUIElement {
        let candidates = [
            app.tabBars.buttons[name].firstMatch,
            app.buttons[name].firstMatch,
            app.cells[name].firstMatch,
            app.staticTexts[name].firstMatch,
            app.descendants(matching: .any)[name].firstMatch,
        ]
        return candidates.first(where: \.exists) ?? candidates[0]
    }

    func testNativeNavigationAndReadOnlyPreview() throws {
        let app = XCUIApplication()
        app.launchArguments = ["--demo"]
        app.launch()
        XCTAssertTrue(app.staticTexts["Vorschau mit Beispieldaten"].waitForExistence(timeout: 10))
        XCTAssertTrue(tab("Übersicht", app: app).exists)
        keepScreenshot("01-uebersicht", app: app)
        tab("Ausgaben", app: app).tap()
        XCTAssertTrue(app.segmentedControls.buttons["Verträge & Kredite"].waitForExistence(timeout: 5))
        keepScreenshot("02-ausgaben", app: app)
        app.segmentedControls.buttons["Verträge & Kredite"].tap()
        XCTAssertTrue(app.staticTexts["Miete Zuhause"].waitForExistence(timeout: 5))
        keepScreenshot("03-vertraege", app: app)
        app.staticTexts["Miete Zuhause"].tap()
        XCTAssertTrue(app.buttons["Bearbeiten"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["Bearbeiten"].isEnabled)
        app.buttons["Schließen"].tap()
        tab("Einnahmen", app: app).tap()
        app.segmentedControls.buttons["Regelmäßig"].tap()
        XCTAssertTrue(app.staticTexts["Gehalt Alex"].waitForExistence(timeout: 5))
        keepScreenshot("04-einnahmen", app: app)
        tab("Haushalt", app: app).tap()
        XCTAssertTrue(app.buttons["Konten"].waitForExistence(timeout: 5))
        keepScreenshot("05-haushalt", app: app)
        app.buttons["Konten"].tap()
        XCTAssertTrue(app.staticTexts["Gemeinschaftskonto"].waitForExistence(timeout: 5))
    }
}
