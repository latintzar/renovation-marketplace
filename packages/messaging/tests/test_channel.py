"""Channel primitives — enum behaviour, capability profiles, LeoMessage."""

from __future__ import annotations

from messaging import (
    EMAIL_CAPABILITIES,
    WEB_CAPABILITIES,
    WHATSAPP_CAPABILITIES,
    Channel,
    ChannelCapabilities,
    LeoMessage,
    MediaAttachment,
)


class TestChannelEnum:
    """Channel is a str-enum to preserve legacy free-string comparisons."""

    def test_web_equals_web_string(self) -> None:
        assert Channel.WEB == "web"

    def test_whatsapp_equals_whatsapp_string(self) -> None:
        assert Channel.WHATSAPP == "whatsapp"

    def test_email_equals_email_string(self) -> None:
        assert Channel.EMAIL == "email"

    def test_auto_is_routing_sentinel(self) -> None:
        assert Channel.AUTO == "auto"
        assert Channel.AUTO != Channel.WEB

    def test_all_is_routing_sentinel(self) -> None:
        assert Channel.ALL == "all"

    def test_enum_is_str_subclass(self) -> None:
        assert isinstance(Channel.WEB, str)


class TestCapabilityProfiles:
    """Pre-baked profiles for the three real surfaces."""

    def test_web_supports_richest_render(self) -> None:
        caps = WEB_CAPABILITIES
        assert caps.channel is Channel.WEB
        assert caps.can_show_preview
        assert caps.can_show_drawer
        assert caps.can_show_tool_cards
        assert caps.can_render_markdown

    def test_whatsapp_has_length_cap(self) -> None:
        caps = WHATSAPP_CAPABILITIES
        assert caps.channel is Channel.WHATSAPP
        assert caps.can_send_template
        assert caps.can_attach_media
        assert caps.max_reply_length == 800
        assert not caps.can_render_markdown

    def test_email_renders_markdown(self) -> None:
        caps = EMAIL_CAPABILITIES
        assert caps.channel is Channel.EMAIL
        assert caps.can_render_markdown
        assert caps.can_attach_media
        assert caps.max_reply_length is None

    def test_copy_does_not_mutate_original(self) -> None:
        mutated = WEB_CAPABILITIES.copy(locale="es-ES")
        assert mutated.locale == "es-ES"
        assert WEB_CAPABILITIES.locale == ""

    def test_copy_preserves_unmutated_fields(self) -> None:
        mutated = WHATSAPP_CAPABILITIES.copy(user_language_hint="ca")
        assert mutated.max_reply_length == 800
        assert mutated.user_language_hint == "ca"


class TestLeoMessage:
    def test_defaults(self) -> None:
        msg = LeoMessage(role="user")
        assert msg.role == "user"
        assert msg.text == ""
        assert msg.media == []

    def test_with_media(self) -> None:
        media = [MediaAttachment(mime_type="image/jpeg", path="/tmp/x.jpg")]
        msg = LeoMessage(role="user", text="pic attached", media=media)
        assert msg.media[0].mime_type == "image/jpeg"


class TestMediaAttachment:
    def test_path_variant(self) -> None:
        att = MediaAttachment(mime_type="image/png", path="/tmp/x.png", caption="diagram")
        assert att.path == "/tmp/x.png"
        assert att.data == ""

    def test_inline_data_variant(self) -> None:
        att = MediaAttachment(mime_type="image/jpeg", data="aGVsbG8=", filename="pic.jpg")
        assert att.data == "aGVsbG8="
        assert att.path == ""


class TestChannelCapabilitiesBuild:
    def test_custom_capability_profile(self) -> None:
        caps = ChannelCapabilities(
            channel=Channel.WEB,
            can_show_preview=True,
            locale="es",
            user_language_hint="es",
        )
        assert caps.channel is Channel.WEB
        assert caps.locale == "es"
        assert caps.user_language_hint == "es"
