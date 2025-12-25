"""
Modeles de donnees pour les pronostics sportifs
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Pronostic:
    """
    Modele de donnees pour un pronostic sportif

    Attributs:
        match: Nom complet du match (ex: "Manchester United vs Liverpool")
        dateTime: Date et heure du match au format ISO (ex: "2025-12-23T15:00:00")
        competition: Nom de la competition (ex: "Premier League")
        sport: Type de sport (ex: "Football", "Basket", "Tennis")
        homeTeam: Nom de l'equipe a domicile
        awayTeam: Nom de l'equipe a l'exterieur
        tipTitle: Titre du pronostic (ex: "Both Teams To Score")
        tipType: Type de pronostic en snake_case (ex: "both_teams_to_score")
        tipText: Texte descriptif du pronostic (ex: "Yes - Both Teams To Score")
        reasonTip: Raison/analyse du pronostic
        odds: Cote decimale (ex: 1.85)
        confidence: Niveau de confiance (optionnel, ex: "high", "medium", "low")
    """
    match: Optional[str] = None
    dateTime: Optional[str] = None
    competition: Optional[str] = None
    sport: Optional[str] = None
    homeTeam: Optional[str] = None
    awayTeam: Optional[str] = None
    tipTitle: Optional[str] = None
    tipType: Optional[str] = None
    tipText: Optional[str] = None
    reasonTip: Optional[str] = None
    odds: Optional[float] = None
    confidence: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convertit le pronostic en dictionnaire"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Pronostic':
        """Cree un pronostic depuis un dictionnaire"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def is_valid(self) -> bool:
        """Verifie si le pronostic contient les informations minimales requises"""
        return bool(self.tipText or self.tipTitle)

    def get_match_key(self) -> tuple:
        """Retourne une cle unique pour identifier ce pronostic (pour deduplication)"""
        return (
            self.match,
            self.dateTime,
            self.homeTeam,
            self.awayTeam,
            self.tipText
        )


@dataclass
class PronosticResponse:
    """
    Modele de reponse pour les scrapers de pronostics

    Attributs:
        success: Indique si le scraping a reussi
        pronostics: Liste des pronostics recuperes
        total_pronostics: Nombre total de pronostics
        error_message: Message d'erreur (si success=False)
        source: Source des pronostics (ex: "FreeSupertips", "FootyAccumulators")
    """
    success: bool
    pronostics: List[Pronostic] = field(default_factory=list)
    total_pronostics: int = 0
    error_message: Optional[str] = None
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convertit la reponse en dictionnaire compatible avec l'API"""
        return {
            "success": self.success,
            "pronostics": [p.to_dict() for p in self.pronostics],
            "total_pronostics": self.total_pronostics,
            "error_message": self.error_message,
            "source": self.source
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PronosticResponse':
        """Cree une reponse depuis un dictionnaire"""
        pronostics = [
            Pronostic.from_dict(p) if isinstance(p, dict) else p
            for p in data.get("pronostics", [])
        ]
        return cls(
            success=data.get("success", False),
            pronostics=pronostics,
            total_pronostics=data.get("total_pronostics", len(pronostics)),
            error_message=data.get("error_message"),
            source=data.get("source")
        )

    @classmethod
    def error(cls, error_message: str, source: Optional[str] = None) -> 'PronosticResponse':
        """Cree une reponse d'erreur"""
        return cls(
            success=False,
            pronostics=[],
            total_pronostics=0,
            error_message=error_message,
            source=source
        )

    @classmethod
    def success_response(cls, pronostics: List[Pronostic], source: Optional[str] = None) -> 'PronosticResponse':
        """Cree une reponse de succes"""
        return cls(
            success=True,
            pronostics=pronostics,
            total_pronostics=len(pronostics),
            error_message=None,
            source=source
        )
