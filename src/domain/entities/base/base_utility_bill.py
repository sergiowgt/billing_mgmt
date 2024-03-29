import re
import calendar
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from src.domain.enums import (ServiceProviderEnum, DocumentTypeEnum,
                              ServiceTypeEnum)


@dataclass
class UtilityBillBase:
    mes_extenso = {'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'abril': 4, 'maio': 5, 'junho': 6,
                   'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12,
                   'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
                   'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12}

    regex_months = 'janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro'
    regex_months_reduced = 'jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez'

    concessionaria: ServiceProviderEnum = ServiceProviderEnum.DESCONHECIDO
    tipo_servico: ServiceTypeEnum = ServiceTypeEnum.DESCONHECIDO
    tipo_documento: DocumentTypeEnum = DocumentTypeEnum.CONTA_CONSUMO
    id_documento = ''
    id_contribuinte = ''
    id_cliente = ''
    id_contrato = ''
    id_conta = ''
    periodo_referencia = ''
    local_consumo = ''
    instalacao = ''
    str_emissao = ''
    str_vencimento = ''
    str_inicio_referencia = ''
    str_fim_referencia = ''
    str_valor = ''
    id_alojamento = ''
    diretorio_google = ''
    str_erro = ''
    folder_id = ''

    dt_inicio_referencia: Optional[date] = None
    dt_fim_referencia: Optional[date] = None
    dt_vencimento: Optional[date] = None
    dt_emissao: Optional[date] = None
    valor: Optional[float] = None
    _is_qualquer_destino: Optional[bool] = None
    is_accounting: bool = False

    @staticmethod
    def _get_data(text, start_str, end_str='', num_chars=0) -> str:
        start_pos = 0
        end_pos = 0
        start_pos = text.find(start_str)

        if start_pos > 0:
            if (num_chars):
                if (len(text) > start_pos+num_chars+1):
                    end_pos = start_pos+len(start_str)+num_chars
            else:
                if (len(text) > start_pos+len(start_str)+1):
                    end_pos = text.find(end_str, start_pos+len(start_str)+1)

        if (start_pos >= end_pos):
            return ""

        start_pos += len(start_str)
        ret = text[start_pos:end_pos]
        ret = ret.replace('\r', '').replace('\n', '')

        if ret:
            ret = ret.strip()

        return ret

    @staticmethod
    def _is_date(str_date) -> bool:
        try:
            _date = datetime.strptime(str_date, '%Y/%m/%d')
        except ValueError:
            return False

        return True

    def _convert_2_default_date(self, str_date: str, format: str, full_month=False) -> str:
        if (not str_date):
            return ''

        str_date = str_date.strip()
        str_date = str_date.replace(' de ', ' ')
        str_date = str_date.replace('  ', ' ')
        str_date = str_date.replace(' de ', ' ')
        str_date = re.sub(r"[\s.-]", "/", str_date)

        vet = str_date.split('/')
        if (len(vet) != 3):
            return ''

        if (full_month):
            mes_extenso = vet[1]
            vet[1] = self.mes_extenso.get(mes_extenso.lower(), '')

        format = format.upper()
        if (format == 'YMD'):
            str_date = f'{vet[0]}/{vet[1]}/{vet[2]}'
        elif (format == 'DMY'):
            str_date = f'{vet[2]}/{vet[1]}/{vet[0]}'

        if not self._is_date(str_date):
            return ''

        return str_date

    def _adjust_data(self) -> None:
        def _str_2_date(value: str) -> date:
            _dt_retorno = None
            if (value):
                try:
                    _dt_retorno = datetime.strptime(value, '%Y/%m/%d')
                except Exception:
                    _dt_retorno = None
            return _dt_retorno

        def _clear_value(value: str) -> str:
            return re.sub(r'[^0-9,]', '', value) if value else ''

        def _clear_data(text: str) -> str:
            return text.replace(' ', '') if text else text

        self.id_documento = _clear_data(self.id_documento)
        self.id_cliente = _clear_data(self.id_cliente)
        self.id_contrato = _clear_data(self.id_contrato)
        self.id_contribuinte = _clear_data(self.id_contribuinte)
        self.local_consumo = _clear_data(self.local_consumo)
        self.str_valor = _clear_value(self.str_valor)

        self.periodo_referencia = self.periodo_referencia.strip()
        self.periodo_referencia = self.periodo_referencia.replace('-', '/')

        self.periodo_referencia.split('~')
        vet = self.periodo_referencia.split('~')
        if (len(vet) == 2):
            self.str_inicio_referencia = self._convert_2_default_date(vet[0].strip(), 'YMD', full_month=False)
            self.str_fim_referencia = self._convert_2_default_date(vet[1].strip(), 'YMD', full_month=False)
        else:
            vet = self.periodo_referencia.split('/')
            if (len(vet) == 2):
                mes = self.mes_extenso.get(vet[0].lower(), '')
                if mes:
                    self.periodo_referencia = f'{vet[1]}/{mes}'
                    self.str_inicio_referencia = self.periodo_referencia + '/1'
                    last_day = calendar.monthrange(int(vet[1]), mes)[1]
                    self.str_fim_referencia = self.periodo_referencia + '/' + str(last_day)
                else:
                    self.periodo_referencia = f'{vet[1]}/{vet[0]}'

        self.dt_vencimento = _str_2_date(self.str_vencimento)
        self.dt_emissao = _str_2_date(self.str_emissao)
        self.dt_inicio_referencia = _str_2_date(self.str_inicio_referencia)
        self.dt_fim_referencia = _str_2_date(self.str_fim_referencia)
        self.dt_vencimento = _str_2_date(self.str_vencimento)

        if (self.str_valor):
            try:
                self.valor = float(self.str_valor.replace(',', '.'))
                if self.tipo_documento == DocumentTypeEnum.NOTA_CREDITO:
                    self.valor = self.valor * -1
            except Exception:
                self.valor = None

    def is_ok(self) -> bool:
        if self.tipo_documento == DocumentTypeEnum.FATURA_ZERADA or self.tipo_documento == DocumentTypeEnum.NOTA_CREDITO:
            if (self.id_cliente == '') and (self.id_contrato == '') and (self.local_consumo == ''):
                return False

            if (self.valor is None) or (self.dt_emissao is None):
                return False

        else:
            if (self.str_vencimento.strip() == ''):
                return False

            if (self.id_cliente == '') and (self.id_contrato == '') and (self.local_consumo == ''):
                return False

            if (self.dt_vencimento is None) or (self.valor is None) or (self.dt_emissao is None):
                return False

        return True

    def _check_account_of_qqd(self, text: str) -> None:
        self._is_qualquer_destino = False
        if "DESTINO" in text:
            if "QQ DESTINO" in text or "QUALQUER DESTINO" in text:
                self._is_qualquer_destino = True
            elif "515593354" in text:
                self._is_qualquer_destino = True

    @property
    def is_qualquer_destino(self) -> bool:
        return self._is_qualquer_destino

    @property
    def nome_calculado(self) -> str:
        if self.is_ok() is False:
            return ''

        if self.id_alojamento == '':
            return ''

        _name_list = ['', 'EDP', 'Galp', 'Aguas', 'Aguas', 'EPAL', 'Altice(MEO)', 'NOS', 'Vodafone']
        _concessionaria = _name_list[self.concessionaria]
        _vet = self.id_alojamento.split('_')
        _alojamento = self.id_alojamento

        if (self.tipo_documento == DocumentTypeEnum.CONTA_CONSUMO):
            dt = self.dt_vencimento if self.dt_vencimento else self.dt_emissao
            part_name = dt.strftime("%Y_%m_%d")
        elif self.tipo_documento == DocumentTypeEnum.CONTA_CONSUMO_RATEIO:
            dt = self.dt_vencimento if self.dt_vencimento else self.dt_emissao
            part_name = dt.strftime("%Y_%m_%d")
        else:
            if self.dt_emissao:
                part_name = self.dt_emissao.strftime("%Y_%m_%d")
            else:
                part_name = datetime.datetime.now().strftime("%Y_%m_%d")

            if (self.tipo_documento == DocumentTypeEnum.NOTA_CREDITO):
                part_name += f'_NC_{self.id_documento}'
            elif (self.tipo_documento == DocumentTypeEnum.FATURA_ZERADA):
                part_name += '_FZ'
        return f'{part_name}_{_concessionaria}_{_alojamento}.pdf'

    def __eq__(self, other):
        if isinstance(other, UtilityBillBase):
            return self.concessionaria == other.concessionaria and \
                self.tipo_servico == other.tipo_servico and \
                self.id_documento == other.id_documento and \
                self.id_contribuinte == other.id_contribuinte and \
                self.id_cliente == other.id_cliente and \
                self.id_contrato == other.id_contrato and  \
                self.str_emissao == other.str_emissao and  \
                self.str_vencimento == other.str_vencimento and  \
                self.str_valor == other.str_valor

        return False

    def __hash__(self):
        return hash((self.concessionaria, self.tipo_servico, self.id_documento,
                    self.id_contribuinte, self.id_cliente, self.id_contrato,
                    self.str_emissao, self.str_vencimento, self.str_valor))
