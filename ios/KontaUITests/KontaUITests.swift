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

    private func button(containing text: String, app: XCUIApplication) -> XCUIElement {
        app.buttons.matching(NSPredicate(format: "label CONTAINS %@", text)).firstMatch
    }

    func testNativeNavigationAndReadOnlyPreview() throws {
        let app = XCUIApplication()
        app.launchArguments = ["--demo"]
        app.launch()
        XCTAssertTrue(app.staticTexts["Vorschau mit Beispieldaten"].waitForExistence(timeout: 10))
        XCTAssertTrue(tab("Übersicht", app: app).exists)
        keepScreenshot("01-uebersicht", app: app)
        tab("Zahlungen", app: app).tap()
        XCTAssertTrue(button(containing: "REWE · Wocheneinkauf", app: app).waitForExistence(timeout: 5))
        XCTAssertFalse(button(containing: "Miete Zuhause", app: app).exists)
        keepScreenshot("02-zahlungen", app: app)
        tab("Verträge", app: app).tap()
        XCTAssertTrue(button(containing: "Miete Zuhause", app: app).waitForExistence(timeout: 5))
        keepScreenshot("03-vertraege", app: app)
        button(containing: "Miete Zuhause", app: app).tap()
        XCTAssertTrue(app.buttons["Bearbeiten"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["Bearbeiten"].isEnabled)
        app.buttons["Schließen"].tap()
        tab("Jobs", app: app).tap()
        XCTAssertTrue(button(containing: "Gehalt Alex", app: app).waitForExistence(timeout: 5))
        keepScreenshot("04-jobs", app: app)
        tab("Sparziele", app: app).tap()
        XCTAssertTrue(app.staticTexts["Euer Sparziel"].waitForExistence(timeout: 5))
        keepScreenshot("05-sparziele", app: app)
        tab("Konten", app: app).tap()
        XCTAssertTrue(button(containing: "Gemeinschaftskonto", app: app).waitForExistence(timeout: 5))
    }
}
