import base64
from webauthn import (
    generate_registration_options, verify_registration_response,
    generate_authentication_options, verify_authentication_response,
)
from webauthn.helpers.base64url_to_bytes import base64url_to_bytes
from webauthn.helpers.bytes_to_base64url import bytes_to_base64url
from webauthn.helpers.structs import (
    RegistrationCredential, AuthenticatorAttestationResponse,
    AuthenticationCredential, AuthenticatorAssertionResponse,
    AuthenticatorSelectionCriteria, UserVerificationRequirement,
    ResidentKeyRequirement, AuthenticatorAttachment,
    PublicKeyCredentialDescriptor,
)
from flask import current_app


RP_ID = "cryptotfg.com"
ORIGIN = "https://cryptotfg.com"


def generate_registration(user):
    options = generate_registration_options(
        rp_id=RP_ID,
        rp_name="CryptoTFG",
        user_id=str(user.UserID).encode(),
        user_name=user.Email,
        user_display_name=user.FirstName,
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
    )

    return options


def verify_registration_response_service(user, data, expected_challenge):
    credential = RegistrationCredential(
        id=data['id'],
        raw_id=base64url_to_bytes(data['rawId']),
        response=AuthenticatorAttestationResponse(
            client_data_json=base64url_to_bytes(data['response']['clientDataJSON']),
            attestation_object=base64url_to_bytes(data['response']['attestationObject']),
        ),
        type=data['type'],
        authenticator_attachment=None,
    )

    verification = verify_registration_response(
        credential=credential,
        expected_challenge=expected_challenge,
        expected_rp_id=RP_ID,
        expected_origin=ORIGIN,
        require_user_verification=True
    )

    # Guardar en el modelo User
    user.register_biometric(
        credential_id=bytes_to_base64url(verification.credential_id),
        public_key=bytes_to_base64url(verification.credential_public_key),
        sign_count=verification.sign_count
    )


def generate_authentication(user):
    return generate_authentication_options(
        rp_id=RP_ID,
        user_verification=UserVerificationRequirement.REQUIRED,
        allow_credentials=[
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(user.BiometricCredentialID))
        ]
    )


def verify_authentication_response_service(user, data, expected_challenge):
    raw_id = base64url_to_bytes(data["rawId"])
    client_data_json = base64url_to_bytes(data["response"]["clientDataJSON"])
    authenticator_data = base64url_to_bytes(data["response"]["authenticatorData"])
    signature = base64url_to_bytes(data["response"]["signature"])
    user_handle = base64url_to_bytes(data["response"]["userHandle"]) if data["response"].get("userHandle") else None

    credential = AuthenticationCredential(
        id=data["id"],
        raw_id=raw_id,
        response=AuthenticatorAssertionResponse(
            client_data_json=client_data_json,
            authenticator_data=authenticator_data,
            signature=signature,
            user_handle=user_handle
        ),
        type=data["type"]
    )

    public_key_bytes = base64url_to_bytes(user.BiometricPublicKey)

    verification = verify_authentication_response(
        credential=credential,
        expected_challenge=expected_challenge,
        expected_rp_id=RP_ID,
        expected_origin=ORIGIN,
        credential_public_key=public_key_bytes,
        credential_current_sign_count=user.SignCount,
        require_user_verification=True
    )

    user.SignCount = verification.new_sign_count
    return verification
