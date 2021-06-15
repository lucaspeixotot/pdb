#!/usr/bin/python3

import yaml

from _io import TextIOWrapper

from .zeta_errors import EZTFIELD, EZTINVREF, ZetaCLIError

ZETA_MODULE_DIR = "."
ZETA_TEMPLATES_DIR = "."
PROJECT_DIR = "."
ZETA_DIR = "."
ZETA_SRC_DIR = "."
ZETA_INCLUDE_DIR = "."


class ZetaYamlLoader(yaml.SafeLoader):
    """Modifies the SafeLoader object and generates a correct
    dictionary-based in the YAML file.
    """
    def __init__(self, stream):
        """YamlRefloader constructor.

        :param stream: default param used for yaml.SafeLoader
        :returns: None
        :rtype: None

        """
        super(ZetaYamlLoader, self).__init__(stream)

    def ref(self, node):
        """Handles ref statements in YAML file and generate a valid
        reference

        :param node: Ref statement with the reference name
        :returns: Reference name
        :rtype: str

        """
        return self.construct_scalar(node)

    def include(self, node):
        """Handles include statements in YAML file and generate a
        valid reference

        :param node: Include statement with the reference name
        :returns: Content of the file passed by include
        :rtype: dict

        """
        include_yaml = dict()
        path = f"{PROJECT_DIR}/../{self.construct_scalar(node)}" if PROJECT_DIR != "." else f"{self.construct_scalar(node)}"
        with open(path, "r") as f:
            include_yaml = yaml.load(f, Loader=ZetaYamlLoader)
        return include_yaml


class Channel(object):
    """Represents a channel written on YAML file.
    """
    def __init__(self,
                 name: str,
                 initial_value: list = None,
                 read_only: bool = False,
                 on_changed: bool = False,
                 size: int = 1,
                 persistent: int = 0,
                 message: str = "") -> None:
        """Channel constructor.

        :param name: Channel name
        :param initial_value: Initial value assigned to channel
        :param read_only: Allows publish operations or not
        :param on_changed: Defines the callback call procedure after a
        publish operation
        :param size: Channel size
        :param persistent: Defines if the channel that must be saved on
        flash
        :returns: None
        :rtype: None

        """
        self.name = name.strip()
        self.read_only = int(read_only)
        self.on_changed = int(on_changed)
        self.size = size
        self.persistent = 1 if persistent else 0
        self.sem = f"zt_{name.lower()}_channel_sem"
        self.id = f"ZT_{name.upper()}_CHANNEL"
        self.initial_value = initial_value
        self.message = message.lower()
        self.message_obj = None
        if initial_value is None:
            self.initial_value = ["0"]
        else:
            self.initial_value = [hex(x) for x in initial_value]

        self.pub_services_obj = []
        self.sub_services_obj = []

    def __repr__(self):
        channel_repr = []
        for k, v in self.__dict__.items():
            channel_repr.append("\n" + f"    {k}: {v}")
        return f"Channel({''.join(channel_repr)});"


class Service(object):
    """Represents a service written on YAML file.
    """
    def __init__(self,
                 name: str,
                 priority: int = 10,
                 stack_size: int = 512,
                 sub_channels: list = [],
                 pub_channels: list = []) -> None:
        """Service constructor.

        :param name: Service name
        :param priority: Defines the service priority
        :param stack_size: Defines the service stack size
        :param sub_channels: Assigns all channels that service must be
        subscribed
        :param pub_channels: Assigns all channels that service must be
        published
        :returns: None
        :rtype: None

        """
        self.name = name
        self.priority = priority
        self.stack_size = stack_size
        self.pub_channels_names = pub_channels
        self.sub_channels_names = sub_channels
        self.pub_channels_obj = []
        self.sub_channels_obj = []


class Config(object):
    def __init__(self,
                 sector_count: int = 4,
                 storage_partition: str = 'storage',
                 storage_period: int = 30) -> None:
        """Config constructor.

        :param sector_count: Sector count that must be used
        :param storage_partition: Defines the storage partition that must be
        used to save channel data
        :param storage_period: Defines the period that zeta will be save
        channel data pending
        :returns: None
        :rtype: None

        """
        self.sector_count = sector_count
        self.storage_partition = storage_partition
        self.storage_period = storage_period


class Message:
    """This object represents the Message defined by the Zeta yaml file.
    """
    def __init__(self,
                 name: str = "undefined_message_name",
                 msg_format: dict = None) -> None:
        """Message constructor.

        :param name: The name of the message, which will be used to reference
        this message.
        :param msg_format: The message format definition in terms of type and
        fields. This can be struct, union and, bitarray.
        :returns: None
        :rtype: None

        """
        self.name = name
        self.msg_format = msg_format if msg_format else {}

    def __repr__(self):
        return f"Message({self.name} -> {self.msg_format})"


class Zeta(object):
    """Represents the Zeta object that has access to services, channels
    and config parameters specified in YAML file.
    """
    def __init__(self, yamlfile: TextIOWrapper) -> None:
        """Zeta constructor.

        :param yamlfile: Zeta yaml file config
        :returns: None
        :rtype: None
        :raise ZetaCLIError: Error creating Channel object or Service object

        """
        ZetaYamlLoader.add_constructor('!ref', ZetaYamlLoader.ref)
        ZetaYamlLoader.add_constructor('!include', ZetaYamlLoader.include)
        yaml_dict = yaml.load(yamlfile, Loader=ZetaYamlLoader)
        try:
            self.config = Config(**yaml_dict['Config'])
        except KeyError:
            self.config = Config()
        self.channels = []
        for channel_description in yaml_dict['Channels']:
            for name, fields in channel_description.items():
                try:
                    self.channels.append(Channel(name, **fields))
                except TypeError as terr:
                    raise ZetaCLIError(
                        f"Error creating Channel object. {terr.__str__()}",
                        EZTFIELD)
        self.services = []
        for service_description in yaml_dict['Services']:
            for name, fields in service_description.items():
                try:
                    self.services.append(Service(name, **fields))
                except TypeError as terr:
                    raise ZetaCLIError(
                        f"Error creating Service object. {terr.__str__()}",
                        EZTFIELD)

        self.messages = []
        try:
            for message_description in yaml_dict['Messages']:
                for name, fields in message_description.items():
                    # print(name, fields)
                    try:
                        self.messages.append(Message(name, fields))
                    except TypeError as terr:
                        raise ZetaCLIError(
                            f"Error creating Message object. {terr.__str__()}",
                            EZTFIELD)
        except KeyError:
            pass

        self.__check_channel_message_relation()
        self.__check_service_channel_relation()

    def __check_service_channel_relation(self) -> None:
        """Checks if the use of !ref is correct or is used some
        nonexistent channel.

        :returns: None
        :rtype: None
        :raise ZetaCLIError: Channel name doesn't exists in channel list.

        """
        for service in self.services:
            for channel_name in service.pub_channels_names:
                for channel in self.channels:
                    if channel.name == channel_name:
                        channel.pub_services_obj.append(service)
                        service.pub_channels_obj.append(channel)
                        break
                else:
                    raise ZetaCLIError(
                        f"Channel {channel_name} does not exists", EZTINVREF)
            for channel_name in service.sub_channels_names:
                for channel in self.channels:
                    if channel.name == channel_name:
                        channel.sub_services_obj.append(service)
                        service.sub_channels_obj.append(channel)
                        break
                else:
                    raise ZetaCLIError(
                        f"Channel {channel_name} does not exists", EZTINVREF)

    def __check_channel_message_relation(self) -> None:
        """Checks if the use of !ref is correct or is used some
        nonexistent channel.

        :returns: None
        :rtype: None
        :raise ZetaCLIError: Channel name doesn't exists in channel list.

        """
        for channel in self.channels:
            if channel.message != "":
                for message in self.messages:
                    if channel.message == message.name.lower():
                        channel.message_obj = message
                        break
                else:
                    raise ZetaCLIError(
                        f"Message format {channel.message} does not exists",
                        EZTINVREF)

    def __process_file(self, yaml_dict: dict):
        """Continues the processing of yamfile

        :param yaml_dict: Dictionary derived by yamlfile
        :returns: None
        :rtype: None

        """
        pass
