import XCTest

@MainActor
final class KontaUITests: XCTestCase {
    private func keepScreenshot(_ name: String, app: XCUIApplication) {
        let attachment = XCTAttachment(screenshot: app.windows.firstMatch.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    private func button(containing text: String, app: XCUIApplication) -> XCUIElement {
        app.buttons.matching(NSPredicate(format: "label CONTAINS %@", text)).firstMatch
    }

    func testSidebarAndReadOnlyPreview() throws {
        let app = XCUIApplication()
        app.launchArguments = ["--demo"]
        app.launch()
        XCTAssertTrue(app.staticTexts["Vorschau mit Beispieldaten"].waitForExistence(timeout: 10))
        keepScreenshot("01-uebersicht", app: app)
        app.outlines.staticTexts["Zahlungen"].click()
        XCTAssertTrue(button(containing: "REWE · Wocheneinkauf", app: app).waitForExistence(timeout: 5))
        XCTAssertFalse(button(containing: "Miete Zuhause", app: app).exists)
        keepScreenshot("02-zahlungen", app: app)
        app.outlines.staticTexts["Verträge"].click()
        XCTAssertTrue(button(containing: "Miete Zuhause", app: app).waitForExistence(timeout: 5))
        keepScreenshot("03-vertraege", app: app)
        app.outlines.staticTexts["Jobs"].click()
        XCTAssertTrue(button(containing: "Gehalt Alex", app: app).waitForExistence(timeout: 5))
        keepScreenshot("04-jobs", app: app)
        app.outlines.staticTexts["Sparziele"].click()
        XCTAssertTrue(app.staticTexts["Euer Sparziel"].waitForExistence(timeout: 5))
        keepScreenshot("05-sparziele", app: app)
        app.outlines.staticTexts["Konten"].click()
        XCTAssertTrue(button(containing: "Gemeinschaftskonto", app: app).waitForExistence(timeout: 5))
        app.buttons["Einstellungen"].click()
        XCTAssertTrue(app.staticTexts["Haushalte"].waitForExistence(timeout: 5))
        keepScreenshot("06-einstellungen", app: app)
    }
}
