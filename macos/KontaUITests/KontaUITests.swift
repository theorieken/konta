import XCTest

@MainActor
final class KontaUITests: XCTestCase {
    private func keepScreenshot(_ name: String, app: XCUIApplication) {
        let attachment = XCTAttachment(screenshot: app.windows.firstMatch.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    func testSidebarAndReadOnlyPreview() throws {
        let app = XCUIApplication()
        app.launchArguments = ["--demo"]
        app.launch()
        XCTAssertTrue(app.staticTexts["Vorschau mit Beispieldaten"].waitForExistence(timeout: 10))
        keepScreenshot("01-uebersicht", app: app)
        app.outlines.staticTexts["Ausgaben"].click()
        XCTAssertTrue(app.radioButtons["Verträge & Kredite"].waitForExistence(timeout: 5))
        keepScreenshot("02-ausgaben", app: app)
        app.outlines.staticTexts["Einnahmen"].click()
        XCTAssertTrue(app.radioButtons["Regelmäßig"].waitForExistence(timeout: 5))
        keepScreenshot("03-einnahmen", app: app)
        app.outlines.staticTexts["Haushalt"].click()
        XCTAssertTrue(app.buttons["Konten"].waitForExistence(timeout: 5))
        keepScreenshot("04-haushalt", app: app)
    }
}
